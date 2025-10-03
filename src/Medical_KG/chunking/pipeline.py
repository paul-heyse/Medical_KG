"""Pipeline entrypoint for semantic chunking."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING, List

from .chunker import Chunk, SemanticChunker, select_profile
from .document import Document
from .facets import FacetGenerator
from .indexing import ChunkIndexer, IndexedChunk
from .metrics import ChunkMetrics, compute_metrics
from .profiles import ChunkingProfile

if TYPE_CHECKING:  # pragma: no cover
    from Medical_KG.embeddings.service import EmbeddingService


@dataclass(slots=True)
class ChunkingResult:
    chunks: List[Chunk]
    metrics: ChunkMetrics
    index_documents: List[IndexedChunk]
    neighbor_merges: List[tuple[Chunk, Chunk]]


class ChunkingPipeline:
    """Run semantic chunking with profile selection and facet generation."""

    def __init__(
        self,
        *,
        facet_generator: FacetGenerator | None = None,
        embedding_service: "EmbeddingService" | None = None,
        indexer: ChunkIndexer | None = None,
    ) -> None:
        self._facet_generator = facet_generator or FacetGenerator()
        self._embedding_service = embedding_service
        self._indexer = indexer or ChunkIndexer()

    def run(self, document: Document, *, profile: ChunkingProfile | None = None) -> ChunkingResult:
        profile = profile or select_profile(document)
        chunker = SemanticChunker(profile)
        chunks = chunker.chunk(document)
        for chunk in chunks:
            self._facet_generator.generate(chunk)
        if self._embedding_service and chunks:
            self._apply_embeddings(chunks)
        metrics = compute_metrics(chunks)
        index_documents: List[IndexedChunk] = []
        neighbor_merges: List[tuple[Chunk, Chunk]] = []
        if self._indexer:
            index_documents = self._indexer.build_documents(chunks)
            neighbor_merges = self._indexer.neighbor_merge(chunks)
        return ChunkingResult(
            chunks=chunks,
            metrics=metrics,
            index_documents=index_documents,
            neighbor_merges=neighbor_merges,
        )

    def _apply_embeddings(self, chunks: List[Chunk]) -> None:
        texts = [chunk.to_embedding_text() for chunk in chunks]
        dense_vectors, sparse_vectors = self._embedding_service.embed_texts(texts)
        for chunk, dense, sparse in zip(chunks, dense_vectors, sparse_vectors):
            chunk.embedding_qwen = dense
            chunk.splade_terms = sparse
        facet_payloads = [
            json.dumps(chunk.facet_json, sort_keys=True) for chunk in chunks if chunk.facet_json
        ]
        if facet_payloads:
            facet_vectors, _ = self._embedding_service.embed_texts(facet_payloads)
            iterator = iter(facet_vectors)
            for chunk in chunks:
                if chunk.facet_json:
                    chunk.facet_embedding_qwen = next(iterator)


__all__ = ["ChunkingPipeline", "ChunkingResult"]
