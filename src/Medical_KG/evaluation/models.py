"""Data models used for evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, MutableMapping, Sequence


@dataclass(frozen=True, slots=True)
class GoldSample:
    query_id: str
    query: str
    intent: str
    relevant_ids: Sequence[str]
    spans: Sequence[Mapping[str, object]] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Prediction:
    query_id: str
    ranked_ids: Sequence[str]
    answer: str | None = None
    citations: Sequence[Mapping[str, object]] = field(default_factory=tuple)


@dataclass(slots=True)
class EvaluationReport:
    retrieval: MutableMapping[str, float]
    extraction: MutableMapping[str, float]
    rag: MutableMapping[str, float]
    drift: MutableMapping[str, float]

    def to_dict(self) -> Mapping[str, Mapping[str, float]]:
        return {
            "retrieval": dict(self.retrieval),
            "extraction": dict(self.extraction),
            "rag": dict(self.rag),
            "drift": dict(self.drift),
        }


__all__ = ["GoldSample", "Prediction", "EvaluationReport"]
