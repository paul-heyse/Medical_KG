"""Chunking quality metrics."""

from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from statistics import mean
from typing import Iterable

from .chunker import Chunk


def _vectorise(text: str) -> dict[str, float]:
    counts: Counter[str] = Counter(token.lower() for token in re.findall(r"[A-Za-z0-9]+", text))
    norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
    return {token: value / norm for token, value in counts.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    shared = set(a) & set(b)
    return sum(a[token] * b[token] for token in shared)


@dataclass(slots=True)
class ChunkMetrics:
    intra_coherence: float
    inter_coherence: float
    boundary_alignment: float
    mean_size: float
    std_size: float
    below_min_tokens: int
    above_max_tokens: int
    intent_recall_at_20: dict[str, float]
    intent_ndcg_at_10: dict[str, float]


def compute_metrics(chunks: Iterable[Chunk]) -> ChunkMetrics:
    chunks = list(chunks)
    if not chunks:
        return ChunkMetrics(0.0, 0.0, 0.0, 0.0, 0.0, 0, 0, {}, {})
    intra = mean(chunk.coherence_score for chunk in chunks)
    boundaries = [chunk.section is not None for chunk in chunks]
    boundary_alignment = sum(boundaries) / len(boundaries)
    sizes = [chunk.tokens for chunk in chunks]
    avg = mean(sizes)
    variance = mean((size - avg) ** 2 for size in sizes) if len(sizes) > 1 else 0.0
    std = variance**0.5
    below_min = sum(1 for size in sizes if size < 120)
    above_max = sum(1 for size in sizes if size > 1200)
    vectors = [_vectorise(chunk.text) for chunk in chunks]
    inter_scores = []
    for left, right in zip(vectors, vectors[1:]):
        inter_scores.append(_cosine(left, right))
    inter = sum(inter_scores) / len(inter_scores) if inter_scores else 1.0
    intent_counts = Counter(chunk.intent.value for chunk in chunks)
    intent_recall = {intent: min(1.0, count / 20.0) for intent, count in intent_counts.items()}
    intent_ndcg = {intent: min(1.0, count / 10.0) for intent, count in intent_counts.items()}
    return ChunkMetrics(
        intra,
        inter,
        boundary_alignment,
        avg,
        std,
        below_min,
        above_max,
        intent_recall,
        intent_ndcg,
    )


__all__ = ["ChunkMetrics", "compute_metrics"]
