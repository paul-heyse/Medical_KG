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
    Callable,
    Generic,
    Literal,
    Mapping,
    MutableMapping,
    Sequence,
    TypeVar,
    cast,
)
from urllib.parse import ParseResult, urlparse

from Medical_KG.compat.httpx import (
    AsyncClientProtocol,
    HTTPError,
    ResponseProtocol,
    create_async_client,
)
from Medical_KG.ingestion.telemetry import (
    HttpBackoffEvent,
    HttpErrorEvent,
    HttpEvent,
    HttpRequestEvent,
    HttpResponseEvent,
    HttpRetryEvent,
    HttpTelemetry,
    PrometheusTelemetry,
    generate_request_id,
)
from Medical_KG.ingestion.types import JSONValue
from Medical_KG.utils.optional_dependencies import HttpxModule, get_httpx_module

HTTPX: HttpxModule = get_httpx_module()

LOGGER = logging.getLogger(__name__)
QUEUE_ALERT_THRESHOLD = 0.8
_EventKey = Literal["request", "response", "retry", "backoff", "error"]
_EVENT_KEYS: tuple[_EventKey, ...] = ("request", "response", "retry", "backoff", "error")


class _NoopMetric:
    def labels(self, *args: object, **kwargs: object) -> "_NoopMetric":  # noqa: D401 - tiny helper
        return self

    def inc(self, *args: object, **kwargs: object) -> None:  # pragma: no cover - no-op metric
        return None

    def observe(self, *args: object, **kwargs: object) -> None:  # pragma: no cover - no-op metric
        return None


HTTP_REQUESTS = _NoopMetric()
HTTP_LATENCY = _NoopMetric()


@dataclass(slots=True)
class RateLimit:
    rate: int
    per: float


@dataclass(slots=True)
class _LimiterSnapshot:
    """Snapshot of limiter state captured during acquisition."""

    wait_time_seconds: float
    queue_depth: int
    queue_capacity: int
    queue_saturation: float


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

    async def acquire(self) -> _LimiterSnapshot:
        async with self._lock:
            now = time()
            while self._events and now - self._events[0] >= self.per:
                self._events.popleft()
            wait_time = 0.0
            if self._events and len(self._events) >= self.rate:
                target = self.per - (now - self._events[0])
                wait_seconds = max(target, 0.0)
                wait_started = time()
                await asyncio.sleep(wait_seconds)
                wait_time = time() - wait_started
                now = time()
                while self._events and now - self._events[0] >= self.per:
                    self._events.popleft()
            self._events.append(now)
            queue_depth = len(self._events)
            saturation = min(queue_depth / self.rate, 1.0) if self.rate else 0.0
            return _LimiterSnapshot(
                wait_time_seconds=wait_time,
                queue_depth=queue_depth,
                queue_capacity=self.rate,
                queue_saturation=saturation,
            )


class _TelemetryRegistry:
    """Manage telemetry callbacks for HTTP lifecycle events."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger
        self._callbacks: dict[_EventKey, list[Callable[[HttpEvent], None]]] = {
            key: [] for key in _EVENT_KEYS
        }
        self._per_host: dict[str, dict[_EventKey, list[Callable[[HttpEvent], None]]]] = {}

    def add(
        self,
        event: _EventKey,
        callback: Callable[[HttpEvent], None],
        *,
        host: str | None = None,
    ) -> None:
        if host is None:
            self._callbacks[event].append(callback)
            return
        host_callbacks = self._per_host.setdefault(
            host,
            {key: [] for key in _EVENT_KEYS},
        )
        host_callbacks[event].append(callback)

    def notify(self, event: _EventKey, payload: HttpEvent, host: str) -> None:
        callbacks = list(self._callbacks[event])
        host_callbacks = self._per_host.get(host)
        if host_callbacks is not None:
            callbacks.extend(host_callbacks[event])
        for callback in callbacks:
            try:
                callback(payload)
            except Exception:  # pragma: no cover - defensive logging
                self._logger.exception("Telemetry callback %s failed", event)


class AsyncHttpClient:
    """HTTP client with retries, rate limiting, and telemetry hooks."""

    def __init__(
        self,
        *,
        timeout: float = 30.0,
        retries: int = 3,
        limits: Mapping[str, RateLimit] | None = None,
        default_rate: RateLimit | None = None,
        headers: MutableMapping[str, str] | None = None,
        on_request: Callable[[HttpRequestEvent], None] | None = None,
        on_response: Callable[[HttpResponseEvent], None] | None = None,
        on_retry: Callable[[HttpRetryEvent], None] | None = None,
        on_backoff: Callable[[HttpBackoffEvent], None] | None = None,
        on_error: Callable[[HttpErrorEvent], None] | None = None,
        telemetry: (
            HttpTelemetry
            | Sequence[HttpTelemetry]
            | Mapping[str, HttpTelemetry | Sequence[HttpTelemetry]]
        )
        | None = None,
        enable_metrics: bool | None = None,
    ) -> None:
        """Construct the asynchronous HTTP client.

        Args:
            timeout: HTTP request timeout in seconds.
            retries: Maximum attempts per request (including the initial attempt).
            limits: Optional per-host rate limits overriding the default limiter.
            default_rate: Fallback rate limit applied when a host has no explicit entry.
            headers: Default headers to attach to every request.
            on_request: Callback accepting :class:`HttpRequestEvent` before dispatching.
            on_response: Callback accepting :class:`HttpResponseEvent` after success.
            on_retry: Callback accepting :class:`HttpRetryEvent` before a retry delay.
            on_backoff: Callback accepting :class:`HttpBackoffEvent` after limiter wait.
            on_error: Callback accepting :class:`HttpErrorEvent` when exceptions occur.
            telemetry: Telemetry helper(s) to register globally or per host.
            enable_metrics: When ``True`` (default if Prometheus available) registers
                :class:`PrometheusTelemetry` automatically.
        """
        http2_enabled = importlib.util.find_spec("h2") is not None
        self._client: AsyncClientProtocol = create_async_client(
            timeout=timeout, headers=headers, http2=http2_enabled
        )
        self._limits: dict[str, RateLimit] = dict(limits or {})
        self._default_rate = default_rate or RateLimit(rate=5, per=1.0)
        self._limiters: dict[str, _SimpleLimiter] = {}
        self._retries = retries
        self._retry_callback: Callable[[str, str, int, Exception], None] | None = None
        self._queue_alert_threshold = QUEUE_ALERT_THRESHOLD
        self._telemetry_registry = _TelemetryRegistry(LOGGER)

        self._register_callback("request", on_request)
        self._register_callback("response", on_response)
        self._register_callback("retry", on_retry)
        self._register_callback("backoff", on_backoff)
        self._register_callback("error", on_error)

        metrics_enabled = enable_client_metrics
        if metrics_enabled is None:
            metrics_enabled = PrometheusTelemetry.is_available()
        if metrics_enabled:
            self._register_telemetry(PrometheusTelemetry())
        self._register_telemetry(telemetry)

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

    def _register_callback(
        self,
        event: _EventKey,
        callback: Callable[[HttpEvent], None] | Callable[[HttpRequestEvent], None] | Callable[[HttpResponseEvent], None] | Callable[[HttpRetryEvent], None] | Callable[[HttpBackoffEvent], None] | Callable[[HttpErrorEvent], None] | None,
        *,
        host: str | None = None,
    ) -> None:
        if callback is None:
            return

        def _adapter(payload: HttpEvent) -> None:
            callback(payload)  # type: ignore[arg-type]

        self._telemetry_registry.add(event, _adapter, host=host)

    def _register_telemetry(
        self,
        telemetry: HttpTelemetry
        | Sequence[HttpTelemetry]
        | Mapping[str, HttpTelemetry | Sequence[HttpTelemetry]]
        | None,
    ) -> None:
        if telemetry is None:
            return
        if isinstance(telemetry, Mapping):
            for host, handler in telemetry.items():
                self._register_telemetry_for_host(handler, host=host)
            return
        if isinstance(telemetry, Sequence) and not isinstance(telemetry, (str, bytes)):
            for handler in telemetry:
                self._register_telemetry_for_host(handler)
            return
        self._register_telemetry_for_host(cast(HttpTelemetry, telemetry))

    def _register_telemetry_for_host(
        self,
        telemetry: HttpTelemetry | Sequence[HttpTelemetry] | None,
        *,
        host: str | None = None,
    ) -> None:
        if telemetry is None:
            return
        if isinstance(telemetry, Sequence) and not isinstance(telemetry, (str, bytes)):
            for handler in telemetry:
                self._register_telemetry_for_host(handler, host=host)
            return
        handler = cast(HttpTelemetry, telemetry)
        self._register_callback("request", getattr(handler, "on_request", None), host=host)
        self._register_callback("response", getattr(handler, "on_response", None), host=host)
        self._register_callback("retry", getattr(handler, "on_retry", None), host=host)
        self._register_callback("backoff", getattr(handler, "on_backoff", None), host=host)
        self._register_callback("error", getattr(handler, "on_error", None), host=host)

    @staticmethod
    def _resolve_request_headers(headers: Mapping[str, str] | None) -> dict[str, str]:
        if not headers:
            return {}
        return {str(key): str(value) for key, value in headers.items()}

    def _emit(self, event: _EventKey, payload: HttpEvent) -> None:
        self._telemetry_registry.notify(event, payload, payload.host)

    async def _prepare_request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str] | None,
    ) -> tuple[_SimpleLimiter, ParseResult, str, str, float]:
        parsed = urlparse(url)
        host = parsed.netloc or parsed.path or ""
        limiter = self._get_limiter(host)
        snapshot = await limiter.acquire()
        request_id = generate_request_id()
        timestamp = time()
        backoff_event = HttpBackoffEvent(
            request_id=request_id,
            url=url,
            method=method,
            host=host,
            timestamp=timestamp,
            wait_time_seconds=snapshot.wait_time_seconds,
            queue_depth=snapshot.queue_depth,
            queue_capacity=snapshot.queue_capacity,
            queue_saturation=snapshot.queue_saturation,
        )
        self._emit("backoff", backoff_event)
        if (
            snapshot.queue_capacity > 0
            and snapshot.queue_saturation >= self._queue_alert_threshold
        ):
            LOGGER.warning(
                "Rate limiter saturation %.2f for host %s",  # pragma: no cover - logging path
                snapshot.queue_saturation,
                host,
                extra={
                    "http_queue_depth": snapshot.queue_depth,
                    "http_queue_capacity": snapshot.queue_capacity,
                    "http_queue_wait_time": snapshot.wait_time_seconds,
                },
            )
        request_event = HttpRequestEvent(
            request_id=request_id,
            url=url,
            method=method,
            host=host,
            timestamp=timestamp,
            headers=self._resolve_request_headers(headers),
        )
        self._emit("request", request_event)
        return limiter, parsed, host, request_id, timestamp

    def _emit_response_event(
        self,
        *,
        request_id: str,
        method: str,
        url: str,
        host: str,
        response: ResponseProtocol,
        start_time: float,
    ) -> None:
        duration = max(time() - start_time, 0.0)
        size = len(getattr(response, "content", b""))
        headers_obj = getattr(response, "headers", None)
        headers = (
            self._resolve_request_headers(headers_obj)
            if isinstance(headers_obj, Mapping)
            else {}
        )
        event = HttpResponseEvent(
            request_id=request_id,
            url=url,
            method=method,
            host=host,
            timestamp=time(),
            status_code=response.status_code,
            duration_seconds=duration,
            response_size_bytes=size,
            headers=headers,
        )
        self._emit("response", event)

    def _emit_retry_event(
        self,
        *,
        request_id: str,
        method: str,
        url: str,
        host: str,
        attempt: int,
        delay_seconds: float,
        will_retry: bool,
        reason: str,
    ) -> None:
        event = HttpRetryEvent(
            request_id=request_id,
            url=url,
            method=method,
            host=host,
            timestamp=time(),
            attempt=attempt,
            delay_seconds=delay_seconds,
            reason=reason,
            will_retry=will_retry,
        )
        self._emit("retry", event)

    def _emit_error_event(
        self,
        *,
        request_id: str,
        method: str,
        url: str,
        host: str,
        exc: Exception,
        retryable: bool,
    ) -> None:
        event = HttpErrorEvent(
            request_id=request_id,
            url=url,
            method=method,
            host=host,
            timestamp=time(),
            error_type=type(exc).__name__,
            message=str(exc),
            retryable=retryable,
        )
        self._emit("error", event)

    def bind_retry_callback(
        self, callback: Callable[[str, str, int, HTTPError], None] | None
    ) -> None:
        """Register a callback invoked prior to retrying a request."""

        self._retry_callback = callback

    async def _execute(self, method: str, url: str, **kwargs: object) -> ResponseProtocol:
        headers = cast(Mapping[str, str] | None, kwargs.get("headers"))
        limiter, parsed, host, request_id, _ = await self._prepare_request(
            method,
            url,
            headers,
        )

        async with limiter:
            backoff = 0.5
            last_error: Exception | None = None
            for attempt in range(1, self._retries + 1):
                try:
                    start = time()
                    response = await self._client.request(method, url, **kwargs)
                    HTTP_REQUESTS.labels(
                        method=method, host=parsed.netloc, status=str(response.status_code)
                    ).inc()
                    HTTP_LATENCY.observe(time() - start)
                    response.raise_for_status()
                    self._emit_response_event(
                        request_id=request_id,
                        method=method,
                        url=url,
                        host=host,
                        response=response,
                        start_time=start,
                    )
                    return response
                except HTTPError as exc:  # pragma: no cover - exercised via tests
                    status = getattr(getattr(exc, "response", None), "status_code", None)
                    retryable = status in {429, 502, 503, 504}
                    self._emit_error_event(
                        request_id=request_id,
                        method=method,
                        url=url,
                        host=host,
                        exc=exc,
                        retryable=retryable,
                    )
                    if not retryable:
                        raise
                    last_error = exc
                    if self._retry_callback is not None and attempt < self._retries:
                        self._retry_callback(method, url, attempt, exc)
                    jitter = random.uniform(0, backoff / 2)
                    delay = backoff + jitter
                    will_retry = attempt < self._retries
                    self._emit_retry_event(
                        request_id=request_id,
                        method=method,
                        url=url,
                        host=host,
                        attempt=attempt,
                        delay_seconds=delay,
                        will_retry=will_retry,
                        reason=type(exc).__name__,
                    )
                    if not will_retry:
                        break
                    await asyncio.sleep(delay)
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
        headers = cast(Mapping[str, str] | None, kwargs.get("headers"))
        limiter, _parsed, host, request_id, _ = await self._prepare_request(
            method,
            url,
            headers,
        )
        start_time = time()
        try:
            async with limiter:
                async with self._client.stream(method, url, **kwargs) as response:
                    response.raise_for_status()
                    self._emit_response_event(
                        request_id=request_id,
                        method=method,
                        url=url,
                        host=host,
                        response=response,
                        start_time=start_time,
                    )
                    yield response
        except Exception as exc:
            retryable = False
            if isinstance(exc, HTTPError):
                status = getattr(getattr(exc, "response", None), "status_code", None)
                retryable = status in {429, 502, 503, 504}
            self._emit_error_event(
                request_id=request_id,
                method=method,
                url=url,
                host=host,
                exc=exc,
                retryable=retryable,
            )
            raise

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
