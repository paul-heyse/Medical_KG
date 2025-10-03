"""Score fusion helpers for retrieval ensembles."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping, MutableMapping, Sequence

from .models import RetrievalResult
from .types import FusionScores


def min_max_normalize(results: Iterable[RetrievalResult]) -> dict[str, float]:
    """Normalize scores to a 0-1 range while preserving ordering."""

    scores = {result.chunk_id: result.score for result in results}
    if not scores:
        return {}
    min_score = min(scores.values())
    max_score = max(scores.values())
    if max_score == min_score:
        return {key: 1.0 for key in scores}
    return {
        key: (value - min_score) / (max_score - min_score)
        for key, value in scores.items()
    }


def weighted_fusion(
    pools: Mapping[str, Iterable[RetrievalResult]],
    weights: Mapping[str, float],
) -> FusionScores:
    """Combine retriever scores using configured weights."""

    normalized: dict[str, dict[str, float]] = {}
    for retriever, results in pools.items():
        normalized[retriever] = min_max_normalize(results)
    fused: MutableMapping[str, float] = defaultdict(float)
    for retriever, scores in normalized.items():
        weight = weights.get(retriever, 0.0)
        if weight == 0.0:
            continue
        for chunk_id, score in scores.items():
            fused[chunk_id] += score * weight
    return dict(fused)


def reciprocal_rank_fusion(
    ranked_lists: Mapping[str, Sequence[RetrievalResult]],
    *,
    k: int,
) -> dict[str, float]:
    """Apply reciprocal-rank fusion when weighted scores are unavailable."""

    fused: MutableMapping[str, float] = defaultdict(float)
    for results in ranked_lists.values():
        for index, result in enumerate(results, start=1):
            fused[result.chunk_id] += 1.0 / (k + index)
    return dict(fused)


__all__ = ["min_max_normalize", "weighted_fusion", "reciprocal_rank_fusion"]
