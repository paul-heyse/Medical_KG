"""Typed helpers for optional third-party dependencies.

These utilities provide minimal Protocol-based facades so that mypy can
reason about optional imports (tiktoken, spaCy, torch, Prometheus, httpx,
locust) without falling back to ``Any``. Runtime behaviour preserves the
existing lazy imports and graceful fallbacks when packages are not installed.
"""

from __future__ import annotations

import importlib
import importlib.util
from dataclasses import dataclass
from types import ModuleType
from typing import (
    Any,
    AsyncContextManager,
    Callable,
    Iterable,
    Mapping,
    Protocol,
    Sequence,
    cast,
)


@dataclass(frozen=True)
class MissingDependencyError(ImportError):
    """Structured import error for optional feature dependencies.

    Parameters mirror the dependency registry so call sites can attach
    actionable context::

        try:
            httpx = optional_import("httpx", feature_name="http")
        except MissingDependencyError as exc:
            logger.error("%s", exc)
            raise

    Attributes
    ----------
    feature_name:
        Human readable name of the feature the caller attempted to use.
    package_name:
        Package (or packages) that must be installed to enable the feature.
    extras_group:
        Optional extras group in ``pyproject.toml`` that installs the dependency.
    install_hint:
        Concrete shell command to resolve the missing dependency.
    docs_url:
        Optional URL pointing to feature documentation.
    """

    feature_name: str
    package_name: str
    extras_group: str | None
    install_hint: str
    docs_url: str | None = None

    def __str__(self) -> str:
        base = (
            f"Feature '{self.feature_name}' requires package '{self.package_name}'.\n"
            f"Install with: {self.install_hint}"
        )
        if self.docs_url:
            return f"{base}\nDocumentation: {self.docs_url}"
        return base


@dataclass(frozen=True)
class DependencyGroup:
    """Registry entry describing optional dependency relationships."""

    packages: tuple[str, ...]
    extras_group: str | None
    docs_url: str | None = None
    modules: tuple[str, ...] | None = None

    @property
    def install_hint(self) -> str:
        if self.extras_group:
            return f"pip install medical-kg[{self.extras_group}]"
        packages = " ".join(self.packages)
        return f"pip install {packages}"

    def package_label(self) -> str:
        if len(self.packages) == 1:
            return self.packages[0]
        return ", ".join(self.packages)

    def import_targets(self) -> tuple[str, ...]:
        if self.modules is not None:
            return self.modules
        targets: list[str] = []
        for package in self.packages:
            normalized = package.replace("-", "_")
            target = normalized.split(".")[0]
            targets.append(target)
        return tuple(targets)


@dataclass(frozen=True)
class DependencyStatus:
    """Computed installation status for an optional dependency group."""

    feature_name: str
    packages: tuple[str, ...]
    extras_group: str | None
    installed: bool
    missing_packages: tuple[str, ...]
    install_hint: str
    docs_url: str | None


DEPENDENCY_REGISTRY: dict[str, DependencyGroup] = {
    "observability": DependencyGroup(
        packages=(
            "prometheus-client",
            "opentelemetry-api",
            "opentelemetry-sdk",
            "opentelemetry-instrumentation-fastapi",
            "opentelemetry-instrumentation-httpx",
        ),
        extras_group="observability",
        docs_url="docs/dependencies.md#observability",
        modules=(
            "prometheus_client",
            "opentelemetry",
            "opentelemetry.sdk",
            "opentelemetry.instrumentation.fastapi",
            "opentelemetry.instrumentation.httpx",
        ),
    ),
    "pdf_processing": DependencyGroup(
        packages=("pypdf", "pdfminer.six"),
        extras_group="pdf",
        docs_url="docs/dependencies.md#pdf-processing",
        modules=("pypdf", "pdfminer"),
    ),
    "embeddings": DependencyGroup(
        packages=("sentence-transformers", "faiss-cpu"),
        extras_group="embeddings",
        docs_url="docs/dependencies.md#embeddings",
        modules=("sentence_transformers", "faiss"),
    ),
    "tokenization": DependencyGroup(
        packages=("tiktoken",),
        extras_group="tokenization",
        docs_url="docs/dependencies.md#tokenization",
        modules=("tiktoken",),
    ),
    "nlp": DependencyGroup(
        packages=("spacy",),
        extras_group="nlp",
        docs_url="docs/dependencies.md#natural-language-processing",
        modules=("spacy",),
    ),
    "gpu": DependencyGroup(
        packages=("torch",),
        extras_group="gpu",
        docs_url="docs/dependencies.md#gpu",
        modules=("torch",),
    ),
    "http": DependencyGroup(
        packages=("httpx",),
        extras_group="http",
        docs_url="docs/dependencies.md#http-clients",
        modules=("httpx",),
    ),
    "caching": DependencyGroup(
        packages=("redis",),
        extras_group="caching",
        docs_url="docs/dependencies.md#caching",
        modules=("redis.asyncio",),
    ),
    "load_testing": DependencyGroup(
        packages=("locust",),
        extras_group="load-testing",
        docs_url="docs/dependencies.md#load-testing",
        modules=("locust",),
    ),
}


def _missing_modules(targets: Iterable[str]) -> tuple[str, ...]:
    missing: list[str] = []
    for module_name in targets:
        try:
            spec = importlib.util.find_spec(module_name)
        except ModuleNotFoundError:
            missing.append(module_name)
            continue
        if spec is None:
            missing.append(module_name)
    return tuple(missing)


def iter_dependency_statuses() -> Iterable[DependencyStatus]:
    """Yield installation status for each optional dependency group."""

    for feature_name, group in DEPENDENCY_REGISTRY.items():
        missing_modules = _missing_modules(group.import_targets())
        installed = not missing_modules
        missing_packages: tuple[str, ...]
        if installed:
            missing_packages = ()
        else:
            missing_map = {
                module_name: package
                for package, module_name in zip(
                    group.packages, group.import_targets(), strict=False
                )
            }
            missing_packages = tuple(
                missing_map.get(module_name, module_name) for module_name in missing_modules
            )

        yield DependencyStatus(
            feature_name=feature_name,
            packages=group.packages,
            extras_group=group.extras_group,
            installed=installed,
            missing_packages=missing_packages,
            install_hint=group.install_hint,
            docs_url=group.docs_url,
        )


def optional_import(
    module: str,
    *,
    feature_name: str | None = None,
    package_name: str | None = None,
    extras_group: str | None = None,
    docs_url: str | None = None,
) -> Any:
    """Import ``module`` or raise :class:`MissingDependencyError` with guidance."""

    try:
        return importlib.import_module(module)
    except ModuleNotFoundError as exc:  # pragma: no cover - exercised via tests
        resolved_feature = feature_name or module
        registry = DEPENDENCY_REGISTRY.get(resolved_feature)
        package_label = package_name
        extras = extras_group
        hint = None
        documentation = docs_url
        if registry is not None:
            package_label = package_label or registry.package_label()
            extras = extras or registry.extras_group
            hint = registry.install_hint
            documentation = documentation or registry.docs_url
        else:
            package_label = package_label or module
        if hint is None:
            if extras:
                hint = f"pip install medical-kg[{extras}]"
            elif package_label:
                hint = f"pip install {package_label}"
            else:
                hint = "pip install missing dependency"
        raise MissingDependencyError(
            feature_name=resolved_feature,
            package_name=package_label or module,
            extras_group=extras,
            install_hint=hint,
            docs_url=documentation,
        ) from exc


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

    def __init__(self, method: str, url: str, **kwargs: Any) -> None: ...

    @property
    def url(self) -> Any: ...

    @property
    def method(self) -> str: ...


class HttpxResponseProtocol(Protocol):
    """Interface consumed by ingestion HTTP utilities."""

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...

    status_code: int
    elapsed: Any | None

    def json(self) -> Any: ...

    def raise_for_status(self) -> None: ...

    @property
    def text(self) -> str: ...

    @property
    def content(self) -> bytes: ...

    @property
    def headers(self) -> dict[str, str]: ...


class HttpxAsyncBaseTransport(Protocol):
    """Subset of ``httpx.AsyncBaseTransport`` used in tests."""

    async def handle_async_request(
        self, request: HttpxRequestProtocol
    ) -> HttpxResponseProtocol: ...


class HttpxAsyncClient(Protocol):
    """Async client features leveraged by the project."""

    def __init__(self, **kwargs: Any) -> None: ...

    async def request(self, method: str, url: str, **kwargs: Any) -> HttpxResponseProtocol: ...

    def stream(
        self, method: str, url: str, **kwargs: Any
    ) -> AsyncContextManager[HttpxResponseProtocol]: ...

    async def get(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpxResponseProtocol: ...

    async def post(
        self,
        url: str,
        *,
        json: Any | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> HttpxResponseProtocol: ...

    async def __aenter__(self) -> "HttpxAsyncClient": ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: Any,
    ) -> None: ...


class RedisClientProtocol(Protocol):
    """Async Redis interactions used by caching layers."""

    async def get(self, key: str) -> bytes | None: ...

    async def setex(self, key: str, seconds: int, value: bytes) -> bool: ...

    async def delete(self, *keys: str) -> int: ...

    async def aclose(self) -> None: ...


class HttpxClient(Protocol):
    """Sync client subset used by embedding clients."""

    def __init__(self, **kwargs: Any) -> None: ...

    def post(self, url: str, *, json: Any | None = None) -> HttpxResponseProtocol: ...

    def close(self) -> None: ...


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


_httpx: ModuleType | None
try:
    _httpx_module = optional_import(
        "httpx",
        feature_name="http",
        package_name="httpx",
    )
except MissingDependencyError:
    _httpx = None
else:
    _httpx = cast(ModuleType, _httpx_module)


_LocustHttpUser: type[LocustUserProtocol] | None
_locust_between: Callable[[float, float], Callable[[], float]] | None
_locust_task: TaskDecoratorFactory | None
try:
    locust_module = optional_import(
        "locust",
        feature_name="load_testing",
        package_name="locust",
    )
except MissingDependencyError:
    _LocustHttpUser = None
    _locust_between = None
    _locust_task = None
else:
    http_user_attr = getattr(locust_module, "HttpUser", None)
    between_attr = getattr(locust_module, "between", None)
    task_attr = getattr(locust_module, "task", None)
    if http_user_attr is None or between_attr is None or task_attr is None:
        _LocustHttpUser = None
        _locust_between = None
        _locust_task = None
    else:
        _LocustHttpUser = cast(type[LocustUserProtocol], http_user_attr)
        _locust_between = cast(Callable[[float, float], Callable[[], float]], between_attr)
        _locust_task = cast(TaskDecoratorFactory, task_attr)


_RedisClient: type[RedisClientProtocol] | None
try:
    redis_module = optional_import(
        "redis.asyncio",
        feature_name="caching",
        package_name="redis",
    )
except MissingDependencyError:
    _RedisClient = None
else:
    _RedisClient = cast(type[RedisClientProtocol], getattr(redis_module, "Redis", None))


def get_tiktoken_encoding(name: str = "cl100k_base") -> TokenEncoder | None:
    """Return the requested tiktoken encoding if the package is installed."""

    try:
        module = optional_import(
            "tiktoken",
            feature_name="tokenization",
            package_name="tiktoken",
        )
    except MissingDependencyError:  # pragma: no cover - optional dependency
        return None

    encoding = module.get_encoding(name)
    return cast(TokenEncoder, encoding)


def load_spacy_pipeline(model: str) -> NLPPipeline | None:
    """Load a spaCy pipeline, returning ``None`` when unavailable."""

    try:
        spacy_module = optional_import(
            "spacy",
            feature_name="nlp",
            package_name="spacy",
        )
    except MissingDependencyError:  # pragma: no cover - optional dependency
        return None

    try:
        pipeline = spacy_module.load(model)
    except OSError:  # pragma: no cover - model missing in runtime environment
        return None
    return cast(NLPPipeline, pipeline)


def get_torch_module() -> TorchModule | None:
    """Return the ``torch`` module if installed."""

    try:
        torch_module = optional_import(
            "torch",
            feature_name="gpu",
            package_name="torch",
        )
    except MissingDependencyError:  # pragma: no cover - optional dependency
        return None
    return cast(TorchModule, torch_module)


def build_gauge(name: str, documentation: str, labelnames: Sequence[str]) -> GaugeProtocol:
    """Construct a Prometheus gauge or a typed no-op substitute."""

    try:
        prom_module = optional_import(
            "prometheus_client",
            feature_name="observability",
            package_name="prometheus-client",
        )
    except MissingDependencyError:  # pragma: no cover - optional dependency
        return _NoopGauge()
    gauge = prom_module.Gauge(name, documentation, labelnames)
    return cast(GaugeProtocol, gauge)


def build_counter(name: str, documentation: str, labelnames: Sequence[str]) -> CounterProtocol:
    """Construct a Prometheus counter or a typed no-op substitute."""

    try:
        prom_module = optional_import(
            "prometheus_client",
            feature_name="observability",
            package_name="prometheus-client",
        )
    except MissingDependencyError:  # pragma: no cover - optional dependency
        return _NoopCounter()
    counter_cls = getattr(prom_module, "Counter", None)
    if counter_cls is None:
        return _NoopCounter()
    counter = counter_cls(name, documentation, labelnames)
    return cast(CounterProtocol, counter)


def build_histogram(
    name: str,
    documentation: str,
    buckets: Sequence[float],
    *,
    labelnames: Sequence[str] | None = None,
) -> HistogramProtocol:
    """Construct a Prometheus histogram or a typed no-op substitute."""

    try:
        prom_module = optional_import(
            "prometheus_client",
            feature_name="observability",
            package_name="prometheus-client",
        )
    except MissingDependencyError:  # pragma: no cover - optional dependency
        return _NoopHistogram()
    histogram_cls = getattr(prom_module, "Histogram", None)
    if histogram_cls is None:
        return _NoopHistogram()
    histogram = histogram_cls(
        name,
        documentation,
        buckets=buckets,
        labelnames=labelnames,
    )
    return cast(HistogramProtocol, histogram)


def get_httpx_module() -> HttpxModule:
    """Return the ``httpx`` module with a typed facade."""

    global _httpx
    if _httpx is None:
        module = optional_import(
            "httpx",
            feature_name="http",
            package_name="httpx",
        )
        _httpx = cast(ModuleType, module)
    return cast(HttpxModule, _httpx)


def build_redis_client(**kwargs: Any) -> RedisClientProtocol:
    """Instantiate a typed Redis client or raise when unavailable."""

    global _RedisClient
    client_cls = _RedisClient
    if client_cls is None:
        module = optional_import(
            "redis.asyncio",
            feature_name="caching",
            package_name="redis",
        )
        client_cls = getattr(module, "Redis", None)
        if client_cls is None:
            raise MissingDependencyError(
                feature_name="caching",
                package_name="redis",
                extras_group=DEPENDENCY_REGISTRY["caching"].extras_group,
                install_hint=DEPENDENCY_REGISTRY["caching"].install_hint,
                docs_url=DEPENDENCY_REGISTRY["caching"].docs_url,
            )
        client_cls = cast(type[RedisClientProtocol], client_cls)
        _RedisClient = client_cls
    assert client_cls is not None
    return client_cls(**kwargs)


def load_locust() -> LocustFacade:
    """Return typed locust helpers, raising when the dependency is absent."""

    global _LocustHttpUser, _locust_between, _locust_task
    if _LocustHttpUser is None or _locust_between is None or _locust_task is None:
        module = optional_import(
            "locust",
            feature_name="load_testing",
            package_name="locust",
        )
        http_user = getattr(module, "HttpUser", None)
        between = getattr(module, "between", None)
        task = getattr(module, "task", None)
        if http_user is None or between is None or task is None:
            raise MissingDependencyError(
                feature_name="load_testing",
                package_name=DEPENDENCY_REGISTRY["load_testing"].package_label(),
                extras_group=DEPENDENCY_REGISTRY["load_testing"].extras_group,
                install_hint=DEPENDENCY_REGISTRY["load_testing"].install_hint,
                docs_url=DEPENDENCY_REGISTRY["load_testing"].docs_url,
            )
        _LocustHttpUser = cast(type[LocustUserProtocol], http_user)
        _locust_between = cast(Callable[[float, float], Callable[[], float]], between)
        _locust_task = cast(TaskDecoratorFactory, task)
    assert _LocustHttpUser is not None
    assert _locust_between is not None
    assert _locust_task is not None
    return LocustFacade(
        HttpUser=_LocustHttpUser,
        between=_locust_between,
        task=_locust_task,
    )


__all__ = [
    "DEPENDENCY_REGISTRY",
    "DependencyGroup",
    "DependencyStatus",
    "MissingDependencyError",
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
    "build_redis_client",
    "iter_dependency_statuses",
    "optional_import",
    "get_httpx_module",
    "get_tiktoken_encoding",
    "get_torch_module",
    "load_locust",
    "load_spacy_pipeline",
]
