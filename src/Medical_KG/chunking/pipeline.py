"""Pipeline entrypoint for semantic chunking."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .chunker import Chunk, SemanticChunker, select_profile
from .document import Document
from .facets import FacetGenerator
from .metrics import ChunkMetrics, compute_metrics
from .profiles import ChunkingProfile


@dataclass(slots=True)
class ChunkingResult:
    chunks: List[Chunk]
    metrics: ChunkMetrics


class ChunkingPipeline:
    """Run semantic chunking with profile selection and facet generation."""

    def __init__(self, *, facet_generator: FacetGenerator | None = None) -> None:
        self._facet_generator = facet_generator or FacetGenerator()

    def run(self, document: Document, *, profile: ChunkingProfile | None = None) -> ChunkingResult:
        profile = profile or select_profile(document)
        chunker = SemanticChunker(profile)
        chunks = chunker.chunk(document)
        for chunk in chunks:
            self._facet_generator.generate(chunk)
        metrics = compute_metrics(chunks)
        return ChunkingResult(chunks=chunks, metrics=metrics)


__all__ = ["ChunkingPipeline", "ChunkingResult"]
