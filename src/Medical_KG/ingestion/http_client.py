from __future__ import annotations

import asyncio
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from time import time
from typing import Any, AsyncIterator, Dict, Mapping, MutableMapping
from urllib.parse import urlparse

import httpx

try:  # pragma: no cover - optional dependency
    from prometheus_client import Counter, Histogram
except ModuleNotFoundError:  # pragma: no cover - fallback in tests
    class _NoopMetric:
        def labels(self, *args: Any, **kwargs: Any) -> "_NoopMetric":
            return self

        def inc(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - noop
            return None

        def observe(self, *_args: Any, **_kwargs: Any) -> None:  # pragma: no cover - noop
            return None

    def Counter(*_args: Any, **_kwargs: Any) -> _NoopMetric:  # type: ignore
        return _NoopMetric()

    def Histogram(*_args: Any, **_kwargs: Any) -> _NoopMetric:  # type: ignore
        return _NoopMetric()

HTTP_REQUESTS = Counter(
    "ingest_http_requests_total",
    "Number of HTTP requests made by the ingestion system",
    labelnames=("method", "host", "status"),
)
HTTP_LATENCY = Histogram(
    "ingest_http_request_duration_seconds",
    "Latency of HTTP requests made by the ingestion system",
    buckets=(0.1, 0.3, 0.6, 1.0, 2.0, 5.0, 10.0),
)


@dataclass(slots=True)
class RateLimit:
    rate: int
    per: float


class _SimpleLimiter:
    def __init__(self, rate: int, per: float) -> None:
        self.rate = rate
        self.per = per
        self._events: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "_SimpleLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        return None

    async def acquire(self) -> None:
        async with self._lock:
            now = time()
            while self._events and now - self._events[0] >= self.per:
                self._events.popleft()
            if len(self._events) >= self.rate:
                wait_time = self.per - (now - self._events[0])
                await asyncio.sleep(max(wait_time, 0))
                now = time()
                while self._events and now - self._events[0] >= self.per:
                    self._events.popleft()
            self._events.append(time())


class AsyncHttpClient:
    """HTTP client with retries, rate limiting, and observability."""

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        retries: int = 3,
        limits: Mapping[str, RateLimit] | None = None,
        default_rate: RateLimit | None = None,
        headers: MutableMapping[str, str] | None = None,
    ) -> None:
        self._client = httpx.AsyncClient(timeout=timeout, headers=headers, http2=True)
        self._limits = limits or {}
        self._default_rate = default_rate or RateLimit(rate=5, per=1.0)
        self._limiters: Dict[str, _SimpleLimiter] = {}
        self._retries = retries

    async def aclose(self) -> None:
        await self._client.aclose()

    def _get_limiter(self, host: str) -> _SimpleLimiter:
        if host not in self._limiters:
            limit = self._limits.get(host, self._default_rate)
            self._limiters[host] = _SimpleLimiter(limit.rate, limit.per)
        return self._limiters[host]

    async def _execute(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        parsed = urlparse(url)
        limiter = self._get_limiter(parsed.netloc)

        async with limiter:
            backoff = 0.5
            last_error: Exception | None = None
            for _ in range(self._retries):
                try:
                    start = time()
                    response = await self._client.request(method, url, **kwargs)
                    HTTP_REQUESTS.labels(method, parsed.netloc, str(response.status_code)).inc()
                    HTTP_LATENCY.observe(time() - start)
                    response.raise_for_status()
                    return response
                except httpx.HTTPError as exc:  # pragma: no cover - exercised via tests
                    last_error = exc
                    HTTP_REQUESTS.labels(method, parsed.netloc, exc.__class__.__name__).inc()
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 5.0)
            if last_error:
                raise last_error
            raise RuntimeError("Retry loop exhausted")

    async def get(self, url: str, *, params: Mapping[str, Any] | None = None, headers: Mapping[str, str] | None = None) -> httpx.Response:
        return await self._execute("GET", url, params=params, headers=headers)

    async def post(self, url: str, *, data: Any | None = None, json: Any | None = None, headers: Mapping[str, str] | None = None) -> httpx.Response:
        return await self._execute("POST", url, data=data, json=json, headers=headers)

    @asynccontextmanager
    async def stream(self, method: str, url: str, **kwargs: Any) -> AsyncIterator[httpx.Response]:
        parsed = urlparse(url)
        limiter = self._get_limiter(parsed.netloc)
        async with limiter:
            async with self._client.stream(method, url, **kwargs) as response:
                HTTP_REQUESTS.labels(method, parsed.netloc, str(response.status_code)).inc()
                HTTP_LATENCY.observe(response.elapsed.total_seconds() if response.elapsed else 0.0)
                response.raise_for_status()
                yield response

    async def get_json(self, url: str, *, params: Mapping[str, Any] | None = None, headers: Mapping[str, str] | None = None) -> Any:
        response = await self.get(url, params=params, headers=headers)
        return response.json()

    async def get_text(self, url: str, *, params: Mapping[str, Any] | None = None, headers: Mapping[str, str] | None = None) -> str:
        response = await self.get(url, params=params, headers=headers)
        return response.text

    async def get_bytes(self, url: str, *, params: Mapping[str, Any] | None = None, headers: Mapping[str, str] | None = None) -> bytes:
        response = await self.get(url, params=params, headers=headers)
        return response.content
