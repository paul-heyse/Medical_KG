"""Typed structures shared across retrieval modules."""
from __future__ import annotations

from typing import Mapping, Sequence, TypedDict


class SearchHit(TypedDict, total=False):
    """Subset of fields expected from OpenSearch responses."""

    chunk_id: str
    doc_id: str
    text: str
    title_path: str
    section: str
    score: float
    metadata: Mapping[str, object]
    start: int
    end: int


class VectorHit(TypedDict, total=False):
    """Subset of fields exposed by vector search results."""

    chunk_id: str
    doc_id: str
    text: str
    score: float
    metadata: Mapping[str, object]
    title_path: str
    section: str
    start: int
    end: int


class NeighborMergeConfig(TypedDict):
    """Configuration for neighbor merging behaviour."""

    min_cosine: float
    max_tokens: int


class MultiGranularityConfig(TypedDict, total=False):
    """Optional configuration for multi-granularity retrieval indexes."""

    enabled: bool
    indexes: Mapping[str, str]


EmbeddingVector = Sequence[float]


__all__ = [
    "SearchHit",
    "VectorHit",
    "NeighborMergeConfig",
    "MultiGranularityConfig",
    "EmbeddingVector",
]

