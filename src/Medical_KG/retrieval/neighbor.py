"""Neighbor merging utilities for retrieval results."""
from __future__ import annotations

from typing import Iterable

from .models import RetrievalResult
from .types import JSONValue


class NeighborMerger:
    """Merge adjacent retrieval results when they belong to the same document."""

    def __init__(self, *, min_cosine: float, max_tokens: int) -> None:
        self._min_cosine = min_cosine
        self._max_tokens = max_tokens

    def merge(self, results: Iterable[RetrievalResult]) -> list[RetrievalResult]:
        merged: list[RetrievalResult] = []
        candidates = list(results)
        for result in candidates:
            if not merged:
                merged.append(result)
                continue
            previous = merged[-1]
            cosine = _as_float(result.metadata.get("cosine"))
            if result.doc_id == previous.doc_id and cosine >= self._min_cosine:
                combined_text = f"{previous.text}\n{result.text}"
                if len(previous.text) + len(result.text) <= self._max_tokens:
                    merged[-1] = previous.clone_with_score(
                        max(previous.score, result.score),
                        rerank=previous.scores.rerank,
                    )
                    merged[-1].text = combined_text
                    continue
            merged.append(result)
        return merged


def filter_by_relationship(
    results: Iterable[RetrievalResult],
    allowed_relationships: Iterable[str] | None,
) -> list[RetrievalResult]:
    allowed = {value.lower() for value in allowed_relationships or []}
    filtered: list[RetrievalResult] = []
    for result in results:
        relationship_raw: JSONValue | None = result.metadata.get("relationship")
        relationship = str(relationship_raw or "").lower()
        if not allowed or not relationship or relationship in allowed:
            filtered.append(result)
    return filtered


def _as_float(value: JSONValue | None) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


__all__ = ["NeighborMerger", "filter_by_relationship"]
