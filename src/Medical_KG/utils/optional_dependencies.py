"""Typed helpers for optional third-party dependencies.

These utilities provide minimal Protocol-based facades so that mypy can
reason about optional imports (tiktoken, spaCy, torch, Prometheus) without
falling back to ``Any``. Runtime behaviour preserves the existing lazy
imports and graceful fallbacks when packages are not installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Protocol, Sequence, cast


if TYPE_CHECKING:  # pragma: no cover - import-time typing help only
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

    def labels(self, **label_values: Any) -> "GaugeProtocol":  # pragma: no cover - delegated
        """Return a child gauge with bound labels."""

    def set(self, value: float) -> None:  # pragma: no cover - delegated
        """Set the gauge to ``value``."""

    def clear(self) -> None:  # pragma: no cover - delegated
        """Reset child metrics."""


class _NoopGauge:
    """Fallback gauge that satisfies :class:`GaugeProtocol`."""

    def labels(self, **label_values: Any) -> "_NoopGauge":
        return self

    def set(self, value: float) -> None:
        return None

    def clear(self) -> None:
        return None


def get_tiktoken_encoding(name: str = "cl100k_base") -> TokenEncoder | None:
    """Return the requested tiktoken encoding if the package is installed."""

    try:
        import tiktoken
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        return None

    encoding: "tiktoken.Encoding" = tiktoken.get_encoding(name)
    return cast(TokenEncoder, encoding)


def load_spacy_pipeline(model: str) -> NLPPipeline | None:
    """Load a spaCy pipeline, returning ``None`` when unavailable."""

    try:
        import spacy
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        return None

    try:
        pipeline: "spacy.language.Language" = spacy.load(model)
    except OSError:  # pragma: no cover - model missing in runtime environment
        return None
    return cast(NLPPipeline, pipeline)


def get_torch_module() -> TorchModule | None:
    """Return the ``torch`` module if installed."""

    try:
        import torch
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        return None
    return cast(TorchModule, torch)


def build_gauge(name: str, documentation: str, labelnames: Sequence[str]) -> GaugeProtocol:
    """Construct a Prometheus gauge or a typed no-op substitute."""

    try:
        from prometheus_client import Gauge as PromGauge
    except ModuleNotFoundError:  # pragma: no cover - optional dependency
        return _NoopGauge()
    gauge: "prometheus_client.Gauge" = PromGauge(name, documentation, labelnames)
    return cast(GaugeProtocol, gauge)


__all__ = [
    "DocProtocol",
    "GaugeProtocol",
    "NLPPipeline",
    "SpanProtocol",
    "TokenEncoder",
    "TorchModule",
    "build_gauge",
    "get_tiktoken_encoding",
    "get_torch_module",
    "load_spacy_pipeline",
]
