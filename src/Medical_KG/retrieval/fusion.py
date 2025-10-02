"""Fusion utilities for combining retriever outputs."""
from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List, Mapping, MutableMapping

from .models import RetrievalResult


def min_max_normalize(results: Iterable[RetrievalResult]) -> Dict[str, float]:
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
) -> Dict[str, float]:
    normalized: Dict[str, Dict[str, float]] = {}
    for retriever, results in pools.items():
        normalized[retriever] = min_max_normalize(results)
    fused: Dict[str, float] = defaultdict(float)
    for retriever, scores in normalized.items():
        weight = weights.get(retriever, 0.0)
        for chunk_id, score in scores.items():
            fused[chunk_id] += score * weight
    return dict(fused)


def reciprocal_rank_fusion(
    ranked_lists: Mapping[str, List[RetrievalResult]],
    *,
    k: int,
) -> Dict[str, float]:
    fused: MutableMapping[str, float] = defaultdict(float)
    for results in ranked_lists.values():
        for index, result in enumerate(results, start=1):
            fused[result.chunk_id] += 1.0 / (k + index)
    return dict(fused)


__all__ = ["min_max_normalize", "weighted_fusion", "reciprocal_rank_fusion"]
