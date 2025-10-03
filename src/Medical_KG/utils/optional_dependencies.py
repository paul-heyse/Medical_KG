"""Typed helpers for optional third-party dependencies.

These utilities provide minimal Protocol-based facades so that mypy can
reason about optional imports (tiktoken, spaCy, torch, Prometheus, httpx,
locust) without falling back to ``Any``. Runtime behaviour preserves the
existing lazy imports and graceful fallbacks when packages are not installed.
"""

from __future__ import annotations

<<<<<<< HEAD
from dataclasses import dataclass
import importlib
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncContextManager,
    Callable,
    Mapping,
    Protocol,
    Sequence,
    cast,
)


if TYPE_CHECKING:  # pragma: no cover - import-time typing help only
    import httpx
    import locust
    import prometheus_client
    import spacy
    import tiktoken
    import torch


class TokenEncoder(Protocol):
    """Subset of the tiktoken ``Encoding`` API that we rely on."""

    def encode(self, text: str) -> Sequence[int]:  # pragma: no cover - thin wrapper
        """Return token ids for the supplied text."""


class SpanProtocol(Protocol):
    """Minimal spaCy span attributes consumed by the project."""

    text: str
    start_char: int
    end_char: int
    label_: str


class DocProtocol(Protocol):
    """Minimal document protocol used by the NER pipeline."""

    ents: Sequence[SpanProtocol]


class NLPPipeline(Protocol):
    """Callable spaCy pipeline contract."""

    def __call__(self, text: str) -> DocProtocol:  # pragma: no cover - delegated to spaCy
        """Process text and return a document with named entities."""


class TorchCudaAccessor(Protocol):
    """Subset of ``torch.cuda`` used for availability checks."""

    def is_available(self) -> bool:  # pragma: no cover - delegated to torch
        """Return ``True`` when at least one CUDA device is accessible."""


class TorchModule(Protocol):
    """Minimal portion of ``torch`` that we reference."""

    cuda: TorchCudaAccessor


class GaugeProtocol(Protocol):
    """Superset of Prometheus ``Gauge`` interactions the codebase performs."""

    def labels(self, **label_values: str) -> "GaugeProtocol":  # pragma: no cover - delegated
        """Return a child gauge with bound labels."""

    def set(self, value: float) -> None:  # pragma: no cover - delegated
        """Set the gauge to ``value``."""

    def clear(self) -> None:  # pragma: no cover - delegated
        """Reset child metrics."""


class CounterProtocol(Protocol):
    """Typed subset of Prometheus Counter interactions."""

    def labels(self, **label_values: Any) -> "CounterProtocol":  # pragma: no cover - delegated
        """Return a child counter with bound labels."""

    def inc(self, amount: float = 1.0) -> None:  # pragma: no cover - delegated
        """Increase the counter by ``amount``."""


class HistogramProtocol(Protocol):
    """Typed subset of Prometheus Histogram interactions."""

    def labels(self, **label_values: Any) -> "HistogramProtocol":  # pragma: no cover - delegated
        """Return a child histogram with bound labels."""

    def observe(self, amount: float) -> None:  # pragma: no cover - delegated
        """Record an observation with value ``amount``."""


class _NoopGauge:
    """Fallback gauge that satisfies :class:`GaugeProtocol`."""

    def labels(self, **_label_values: Any) -> "_NoopGauge":
        return self

    def set(self, value: float) -> None:
        return None

    def clear(self) -> None:
        return None


class _NoopCounter:
    """Fallback counter that mirrors Prometheus semantics."""

    def labels(self, **_label_values: Any) -> "_NoopCounter":
        return self

    def inc(self, amount: float = 1.0) -> None:
        return None


class _NoopHistogram:
    """Fallback histogram that mirrors Prometheus semantics."""

    def labels(self, **_label_values: Any) -> "_NoopHistogram":
        return self

    def observe(self, amount: float) -> None:
        return None


class HttpxRequestProtocol(Protocol):
    """Minimal constructor signature for ``httpx.Request`` objects."""

    def __init__(self, method: str, url: str, **kwargs: Any) -> None:
        ...

    @property
    def url(self) -> Any:
        ...

    @property
    def method(self) -> str:
        ...


class HttpxResponseProtocol(Protocol):
    """Interface consumed by ingestion HTTP utilities."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        ...

    status_code: int
    elapsed: Any | None

    def json(self) -> Any:
        ...

    def raise_for_status(self) -> None:
        ...

    @property
    def text(self) -> str:
        ...

    @property
    def content(self) -> bytes:
        ...

    @property
    def headers(self) -> dict[str, str]:
        ...


class HttpxAsyncBaseTransport(Protocol):
    """Subset of ``httpx.AsyncBaseTransport`` used in tests."""

    async def handle_async_request(self, request: HttpxRequestProtocol) -> HttpxResponseProtocol:
        ...


class HttpxAsyncClient(Protocol):
    """Async client features leveraged by the project."""

    def __init__(self, **kwargs: Any) -> None:
        ...

    async def request(self, method: str, url: str, **kwargs: Any) -> HttpxResponseProtocol:
        ...

    async def aclose(self) -> None:
        ...

    def stream(self, method: str, url: str, **kwargs: Any) -> AsyncContextManager[HttpxResponseProtocol]:
        ...

    async def get(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpxResponseProtocol:
        ...

    async def post(
        self,
        url: str,
        *,
        json: Any | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpxResponseProtocol:
        ...

    async def __aenter__(self) -> HttpxAsyncClient:
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> None:
        ...


class HttpxClient(Protocol):
    """Sync client subset used by embedding clients."""

    def __init__(self, **kwargs: Any) -> None:
        ...

    def post(self, url: str, *, json: Any | None = None) -> HttpxResponseProtocol:
        ...

    def close(self) -> None:
        ...


class HttpxModule(Protocol):
    """Module-level contract for ``httpx`` access."""

    AsyncClient: type[HttpxAsyncClient]
    Client: type[HttpxClient]
    Request: type[HttpxRequestProtocol]
    Response: type[HttpxResponseProtocol]
    AsyncBaseTransport: type[HttpxAsyncBaseTransport]
    ASGITransport: type[Any]
    TimeoutException: type[Exception]
    HTTPError: type[Exception]


class LocustUserProtocol(Protocol):
    """Shape of ``locust.HttpUser`` that tests rely on."""

    client: Any
    wait_time: Callable[[], float]


TaskDecorator = Callable[[Callable[..., Any]], Callable[..., Any]]
TaskDecoratorFactory = Callable[..., TaskDecorator]


@dataclass(frozen=True)
class LocustFacade:
    """Typed accessor for locust helpers."""

    HttpUser: type[LocustUserProtocol]
    between: Callable[[float, float], Callable[[], float]]
    task: TaskDecoratorFactory


try:  # pragma: no cover - optional dependency wiring
    import httpx as _httpx  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - tests guard against this at runtime
    _httpx = None


try:  # pragma: no cover - optional dependency wiring
    from locust import HttpUser as _LocustHttpUser, between as _locust_between, task as _locust_task  # type: ignore[import-not-found]
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    _LocustHttpUser = None
    _locust_between = None
    _locust_task = None


def get_tiktoken_encoding(name: str = "cl100k_base") -> TokenEncoder | None:
    """Return the requested tiktoken encoding if the package is installed."""

    try:
        module = importlib.import_module("tiktoken")
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        return None

    encoding = module.get_encoding(name)
    return cast(TokenEncoder, encoding)


def load_spacy_pipeline(model: str) -> NLPPipeline | None:
    """Load a spaCy pipeline, returning ``None`` when unavailable."""

    try:
        spacy_module = importlib.import_module("spacy")
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        return None

    try:
        pipeline = spacy_module.load(model)
    except OSError:  # pragma: no cover - model missing in runtime environment
        return None
    return cast(NLPPipeline, pipeline)


def get_torch_module() -> TorchModule | None:
    """Return the ``torch`` module if installed."""

    try:
        torch_module = importlib.import_module("torch")
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        return None
    return cast(TorchModule, torch_module)


def build_gauge(name: str, documentation: str, labelnames: Sequence[str]) -> GaugeProtocol:
    """Construct a Prometheus gauge or a typed no-op substitute."""

    try:
        prom_module = importlib.import_module("prometheus_client")
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        return _NoopGauge()
    gauge = prom_module.Gauge(name, documentation, labelnames)
    return cast(GaugeProtocol, gauge)


def build_counter(name: str, documentation: str, labelnames: Sequence[str]) -> CounterProtocol:
    """Construct a Prometheus counter or a typed no-op substitute."""

    try:
        from prometheus_client import Counter as PromCounter  # type: ignore[import-not-found]
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        return _NoopCounter()
    counter: "prometheus_client.Counter" = PromCounter(name, documentation, labelnames)
    return cast(CounterProtocol, counter)


def build_histogram(name: str, documentation: str, buckets: Sequence[float]) -> HistogramProtocol:
    """Construct a Prometheus histogram or a typed no-op substitute."""

    try:
        from prometheus_client import Histogram as PromHistogram  # type: ignore[import-not-found]
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        return _NoopHistogram()
    histogram: "prometheus_client.Histogram" = PromHistogram(name, documentation, buckets=buckets)
    return cast(HistogramProtocol, histogram)


def get_httpx_module() -> HttpxModule:
    """Return the ``httpx`` module with a typed facade."""

    if _httpx is None:
        raise ModuleNotFoundError(
            "httpx is required but not installed. Install the project dependencies to run HTTP-bound features."
        )
    return cast(HttpxModule, _httpx)


def load_locust() -> LocustFacade:
    """Return typed locust helpers, raising when the dependency is absent."""

    if _LocustHttpUser is None or _locust_between is None or _locust_task is None:
        raise ModuleNotFoundError(
            "locust is required to execute load tests. Install it before running ops/load_test/locustfile.py."
        )
    return LocustFacade(
        HttpUser=cast(type[LocustUserProtocol], _LocustHttpUser),
        between=cast(Callable[[float, float], Callable[[], float]], _locust_between),
        task=cast(TaskDecoratorFactory, _locust_task),
    )


__all__ = [
    "CounterProtocol",
    "DocProtocol",
    "GaugeProtocol",
    "HistogramProtocol",
    "HttpxAsyncBaseTransport",
    "HttpxAsyncClient",
    "HttpxClient",
    "HttpxModule",
    "HttpxRequestProtocol",
    "HttpxResponseProtocol",
    "LocustFacade",
    "LocustUserProtocol",
    "NLPPipeline",
    "SpanProtocol",
    "TokenEncoder",
    "TorchModule",
    "build_counter",
    "build_gauge",
    "build_histogram",
    "get_httpx_module",
    "get_tiktoken_encoding",
    "get_torch_module",
    "load_locust",
    "load_spacy_pipeline",
]
