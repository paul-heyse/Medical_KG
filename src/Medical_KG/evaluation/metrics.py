"""Metric computations for retrieval and extraction."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence


@dataclass(frozen=True, slots=True)
class RetrievalMetrics:
    recall_at_10: float
    ndcg_at_10: float
    mrr: float


def compute_retrieval_metrics(
    relevant_ids: Sequence[str], ranked_ids: Sequence[str]
) -> RetrievalMetrics:
    rel_set = set(relevant_ids)
    hits = [idx for idx, doc_id in enumerate(ranked_ids[:10], start=1) if doc_id in rel_set]
    recall = len(hits) / max(len(relevant_ids), 1)
    ndcg = _ndcg(relevant_ids, ranked_ids, k=10)
    mrr = 0.0
    for idx, doc_id in enumerate(ranked_ids, start=1):
        if doc_id in rel_set:
            mrr = 1 / idx
            break
    return RetrievalMetrics(recall_at_10=recall, ndcg_at_10=ndcg, mrr=mrr)


def extraction_f1(truth: Sequence[str], predicted: Sequence[str]) -> float:
    truth_set = set(truth)
    pred_set = set(predicted)
    tp = len(truth_set & pred_set)
    if tp == 0:
        return 0.0
    precision = tp / len(pred_set)
    recall = tp / len(truth_set)
    return 2 * precision * recall / (precision + recall)


def hallucination_rate(claims: Sequence[Mapping[str, Sequence[Mapping[str, object]]]]) -> float:
    total = len(claims)
    if total == 0:
        return 0.0
    missing = sum(1 for claim in claims if not claim.get("citations"))
    return missing / total


def _ndcg(relevant_ids: Sequence[str], ranked_ids: Sequence[str], k: int) -> float:
    rel_set = set(relevant_ids)
    dcg = 0.0
    for idx, doc_id in enumerate(ranked_ids[:k], start=1):
        if doc_id in rel_set:
            dcg += 1 / math.log2(idx + 1)
    ideal_hits = min(len(relevant_ids), k)
    idcg = sum(1 / math.log2(idx + 1) for idx in range(1, ideal_hits + 1))
    if idcg == 0:
        return 0.0
    return dcg / idcg


def drift_delta(current: Mapping[str, float], previous: Mapping[str, float]) -> Mapping[str, float]:
    delta: dict[str, float] = {}
    for key, current_value in current.items():
        prev = previous.get(key, current_value)
        delta[key] = current_value - prev
    return delta


__all__ = [
    "RetrievalMetrics",
    "compute_retrieval_metrics",
    "extraction_f1",
    "hallucination_rate",
    "drift_delta",
]
