from __future__ import annotations

import asyncio
import importlib.util
import logging
import random
from collections import deque
from contextlib import asynccontextmanager
from dataclasses import dataclass
from time import time
from types import TracebackType
from typing import (
    AsyncIterator,
    Generic,
    Mapping,
    MutableMapping,
    TypeVar,
    cast,
)
from urllib.parse import urlparse

from Medical_KG.compat.httpx import (
    AsyncClientProtocol,
    HTTPError,
    ResponseProtocol,
    create_async_client,
)
from Medical_KG.ingestion.types import JSONValue
from Medical_KG.utils.optional_dependencies import (
    CounterProtocol,
    HistogramProtocol,
    HttpxModule,
    build_counter,
    build_histogram,
    get_httpx_module,
)

HTTPX: HttpxModule = get_httpx_module()

HTTP_REQUESTS: CounterProtocol = build_counter(
    "ingest_http_requests_total",
    "Number of HTTP requests made by the ingestion system",
    labelnames=("method", "host", "status"),
)
HTTP_LATENCY: HistogramProtocol = build_histogram(
    "ingest_http_request_duration_seconds",
    "Latency of HTTP requests made by the ingestion system",
    buckets=(0.1, 0.3, 0.6, 1.0, 2.0, 5.0, 10.0),
)

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class RateLimit:
    rate: int
    per: float


JSONBodyT = TypeVar("JSONBodyT", bound=JSONValue)


@dataclass(slots=True)
class JsonResponse(Generic[JSONBodyT]):
    url: str
    status_code: int
    data: JSONBodyT


@dataclass(slots=True)
class TextResponse:
    url: str
    status_code: int
    text: str


@dataclass(slots=True)
class BytesResponse:
    url: str
    status_code: int
    content: bytes


class _SimpleLimiter:
    def __init__(self, rate: int, per: float) -> None:
        self.rate = rate
        self.per = per
        self._events: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "_SimpleLimiter":
        await self.acquire()
        return self

    async def __aexit__(self, *_exc: object) -> None:
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
        http2_enabled = importlib.util.find_spec("h2") is not None
        self._client: AsyncClientProtocol = create_async_client(
            timeout=timeout, headers=headers, http2=http2_enabled
        )
        self._limits: dict[str, RateLimit] = dict(limits or {})
        self._default_rate = default_rate or RateLimit(rate=5, per=1.0)
        self._limiters: dict[str, _SimpleLimiter] = {}
        self._retries = retries

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "AsyncHttpClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        close_error: Exception | None = None
        try:
            await self.aclose()
        except Exception as err:  # pragma: no cover - rare cleanup failure
            close_error = err
            if exc is not None:
                LOGGER.warning(
                    "AsyncHttpClient cleanup failed during exception handling: %s",
                    err,
                )
        if close_error is not None and exc_type is None:
            raise close_error
        return False

    def _get_limiter(self, host: str) -> _SimpleLimiter:
        if host not in self._limiters:
            limit = self._limits.get(host, self._default_rate)
            self._limiters[host] = _SimpleLimiter(limit.rate, limit.per)
        return self._limiters[host]

    async def _execute(self, method: str, url: str, **kwargs: object) -> ResponseProtocol:
        parsed = urlparse(url)
        limiter = self._get_limiter(parsed.netloc)

        async with limiter:
            backoff = 0.5
            last_error: Exception | None = None
            for _ in range(self._retries):
                try:
                    start = time()
                    response = await self._client.request(method, url, **kwargs)
                    HTTP_REQUESTS.labels(
                        method=method, host=parsed.netloc, status=str(response.status_code)
                    ).inc()
                    HTTP_LATENCY.observe(time() - start)
                    response.raise_for_status()
                    return response
                except HTTPError as exc:  # pragma: no cover - exercised via tests
                    status = getattr(getattr(exc, "response", None), "status_code", None)
                    if status not in {429, 502, 503, 504}:
                        raise
                    last_error = exc
                    HTTP_REQUESTS.labels(
                        method=method, host=parsed.netloc, status=exc.__class__.__name__
                    ).inc()
                    jitter = random.uniform(0, backoff / 2)
                    await asyncio.sleep(backoff + jitter)
                    backoff = min(backoff * 2, 5.0)
            if last_error:
                raise last_error
            raise RuntimeError("Retry loop exhausted")

    async def get(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ResponseProtocol:
        return await self._execute("GET", url, params=params, headers=headers)

    async def post(
        self,
        url: str,
        *,
        data: object | None = None,
        json: JSONValue | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> ResponseProtocol:
        return await self._execute("POST", url, data=data, json=json, headers=headers)

    @asynccontextmanager
    async def stream(
        self, method: str, url: str, **kwargs: object
    ) -> AsyncIterator[ResponseProtocol]:
        parsed = urlparse(url)
        limiter = self._get_limiter(parsed.netloc)
        async with limiter:
            async with self._client.stream(method, url, **kwargs) as response:
                HTTP_REQUESTS.labels(
                    method=method, host=parsed.netloc, status=str(response.status_code)
                ).inc()
                HTTP_LATENCY.observe(response.elapsed.total_seconds() if response.elapsed else 0.0)
                response.raise_for_status()
                yield response

    async def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> JsonResponse[JSONValue]:
        response = await self.get(url, params=params, headers=headers)
        # ``httpx.Response.json`` returns ``Any``; narrow to ``JSONValue`` for callers.
        payload = cast(JSONValue, response.json())
        return JsonResponse(url=url, status_code=response.status_code, data=payload)

    async def get_text(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> TextResponse:
        response = await self.get(url, params=params, headers=headers)
        return TextResponse(url=url, status_code=response.status_code, text=response.text)

    async def get_bytes(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> BytesResponse:
        response = await self.get(url, params=params, headers=headers)
        return BytesResponse(url=url, status_code=response.status_code, content=response.content)

    def set_rate_limit(self, host: str, limit: RateLimit) -> None:
        """Override the per-host rate limit."""

        self._limits[host] = limit
        if host in self._limiters:
            self._limiters[host] = _SimpleLimiter(limit.rate, limit.per)
