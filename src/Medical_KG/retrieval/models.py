"""Core dataclasses and type helpers for retrieval orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping

from .types import JSONValue, MultiGranularityConfig, NeighborMergeConfig


@dataclass(slots=True)
class RetrieverTiming:
    component: str
    duration_ms: float


@dataclass(slots=True)
class RetrieverScores:
    bm25: float | None = None
    splade: float | None = None
    dense: float | None = None
    fused: float | None = None
    rerank: float | None = None

    def as_dict(self) -> dict[str, float]:
        payload: dict[str, float] = {}
        if self.bm25 is not None:
            payload["bm25"] = self.bm25
        if self.splade is not None:
            payload["splade"] = self.splade
        if self.dense is not None:
            payload["dense"] = self.dense
        if self.fused is not None:
            payload["fused"] = self.fused
        if self.rerank is not None:
            payload["rerank"] = self.rerank
        return payload


@dataclass(slots=True)
class RetrievalResult:
    chunk_id: str
    doc_id: str
    text: str
    title_path: str | None
    section: str | None
    score: float
    scores: RetrieverScores = field(default_factory=RetrieverScores)
    start: int | None = None
    end: int | None = None
    metadata: dict[str, JSONValue] = field(default_factory=dict)

    def clone_with_score(self, score: float, *, rerank: float | None = None) -> "RetrievalResult":
        updated_scores = RetrieverScores(
            bm25=self.scores.bm25,
            splade=self.scores.splade,
            dense=self.scores.dense,
            fused=self.scores.fused,
            rerank=rerank if rerank is not None else self.scores.rerank,
        )
        return RetrievalResult(
            chunk_id=self.chunk_id,
            doc_id=self.doc_id,
            text=self.text,
            title_path=self.title_path,
            section=self.section,
            score=score,
            scores=updated_scores,
            start=self.start,
            end=self.end,
            metadata=self.metadata,
        )


@dataclass(slots=True)
class RetrievalRequest:
    query: str
    top_k: int = 20
    from_: int = 0
    filters: Mapping[str, JSONValue] = field(default_factory=dict)
    intent: str | None = None
    rerank_enabled: bool | None = None
    explain: bool = False


@dataclass(slots=True)
class RetrievalResponse:
    results: list[RetrievalResult]
    timings: list[RetrieverTiming]
    expanded_terms: Mapping[str, float]
    intent: str
    latency_ms: float
    from_: int
    size: int
    metadata: dict[str, JSONValue] = field(default_factory=dict)


@dataclass(slots=True)
class CachedItem:
    value: object
    expires_at: datetime


@dataclass(slots=True)
class RetrieverContext:
    """Contextual knobs derived from configuration and runtime intent."""

    boosts: Mapping[str, float]
    filters: Mapping[str, JSONValue]
    top_k: int
    weights: Mapping[str, float]
    rrf_k: int
    rerank_top_n: int
    rerank_enabled: bool
    neighbor_merge: NeighborMergeConfig
    multi_granularity: MultiGranularityConfig


def merge_metadata(*items: Mapping[str, JSONValue]) -> dict[str, JSONValue]:
    merged: dict[str, JSONValue] = {}
    for item in items:
        merged.update({k: v for k, v in item.items() if v is not None})
    return merged


def normalize_filters(filters: Mapping[str, JSONValue] | None) -> dict[str, JSONValue]:
    if not filters:
        return {}
    normalized: dict[str, JSONValue] = {}
    for key, value in filters.items():
        if value is None:
            continue
        normalized[key] = value
    return normalized
