"""Typed helpers for optional spaCy dependency."""

from __future__ import annotations

import importlib
from typing import Callable, Protocol, Sequence, cast


class SpanProtocol(Protocol):
    text: str
    start_char: int
    end_char: int
    label_: str


class DocProtocol(Protocol):
    @property
    def ents(self) -> Sequence[SpanProtocol]: ...


PipelineProtocol = Callable[[str], DocProtocol]


def load_pipeline(model: str) -> PipelineProtocol | None:
    """Load a spaCy pipeline if the dependency is available."""

    spec = importlib.util.find_spec("spacy")
    if spec is None:
        return None
    module = importlib.import_module("spacy")
    load = getattr(module, "load", None)
    if not callable(load):
        return None
    pipeline = load(model)
    return cast(PipelineProtocol, pipeline)


__all__ = ["DocProtocol", "PipelineProtocol", "SpanProtocol", "load_pipeline"]
