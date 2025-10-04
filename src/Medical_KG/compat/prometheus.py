"""Prometheus client wrappers with typed fallbacks."""

from __future__ import annotations

from typing import Any, Callable, Protocol, cast

from Medical_KG.utils.optional_dependencies import (
    MissingDependencyError,
    optional_import,
)


class CounterLike(Protocol):
    """Protocol modelling the Counter API we rely on."""

    def labels(self, *label_values: str, **label_kwargs: str) -> "CounterLike": ...

    def inc(self, amount: float = 1.0) -> None: ...


class HistogramLike(Protocol):
    """Protocol modelling the Histogram API we rely on."""

    def labels(self, *label_values: str, **label_kwargs: str) -> "HistogramLike": ...

    def observe(self, value: float) -> None: ...


class GaugeLike(Protocol):
    """Protocol modelling the Gauge API we rely on."""

    def labels(self, *label_values: str, **label_kwargs: str) -> "GaugeLike": ...

    def set(self, value: float | int) -> None: ...

    def clear(self) -> None: ...


class _NoopMetric:
    """Fallback metric when prometheus_client is unavailable."""

    def labels(self, *args: str, **kwargs: str) -> "_NoopMetric":  # pragma: no cover - simple noop
        return self

    def inc(self, *_: Any, **__: Any) -> None:  # pragma: no cover - simple noop
        return None

    def observe(self, *_: Any, **__: Any) -> None:  # pragma: no cover - simple noop
        return None

    def set(self, *_: Any, **__: Any) -> None:  # pragma: no cover - simple noop
        return None

    def clear(self) -> None:  # pragma: no cover - simple noop
        return None


try:  # pragma: no cover - exercised only when dependency installed
    _prometheus = optional_import(
        "prometheus_client",
        feature_name="observability",
        package_name="prometheus-client",
    )
except MissingDependencyError:  # pragma: no cover - default for tests
    _prometheus = None

_CounterFactory: Callable[..., CounterLike] | None = None
_HistogramFactory: Callable[..., HistogramLike] | None = None
_GaugeFactory: Callable[..., GaugeLike] | None = None
if _prometheus is not None:
    _CounterFactory = cast(Callable[..., CounterLike], getattr(_prometheus, "Counter", None))
    _HistogramFactory = cast(Callable[..., HistogramLike], getattr(_prometheus, "Histogram", None))
    _GaugeFactory = cast(Callable[..., GaugeLike], getattr(_prometheus, "Gauge", None))


def Counter(*args: Any, **kwargs: Any) -> CounterLike:
    """Create a Counter metric or a noop fallback."""

    if _CounterFactory is not None:
        return _CounterFactory(*args, **kwargs)
    return _NoopMetric()


def Histogram(*args: Any, **kwargs: Any) -> HistogramLike:
    """Create a Histogram metric or a noop fallback."""

    if _HistogramFactory is not None:
        return _HistogramFactory(*args, **kwargs)
    return _NoopMetric()


def Gauge(*args: Any, **kwargs: Any) -> GaugeLike:
    """Create a Gauge metric or a noop fallback."""

    if _GaugeFactory is not None:
        return _GaugeFactory(*args, **kwargs)
    return _NoopMetric()


__all__ = [
    "Counter",
    "CounterLike",
    "Gauge",
    "GaugeLike",
    "Histogram",
    "HistogramLike",
]
