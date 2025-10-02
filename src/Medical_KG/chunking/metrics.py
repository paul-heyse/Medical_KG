"""Chunking quality metrics."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable

from .chunker import Chunk


@dataclass(slots=True)
class ChunkMetrics:
    intra_coherence: float
    boundary_alignment: float
    mean_size: float
    std_size: float


def compute_metrics(chunks: Iterable[Chunk]) -> ChunkMetrics:
    chunks = list(chunks)
    if not chunks:
        return ChunkMetrics(0.0, 0.0, 0.0, 0.0)
    intra = mean(chunk.coherence_score for chunk in chunks)
    boundaries = [chunk.section is not None for chunk in chunks]
    boundary_alignment = sum(boundaries) / len(boundaries)
    sizes = [chunk.tokens for chunk in chunks]
    avg = mean(sizes)
    variance = mean((size - avg) ** 2 for size in sizes) if len(sizes) > 1 else 0.0
    std = variance ** 0.5
    return ChunkMetrics(intra, boundary_alignment, avg, std)


__all__ = ["ChunkMetrics", "compute_metrics"]
