"""Pipeline entrypoint for semantic chunking."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
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
class FacetVectorRecord:
    chunk_id: str
    doc_id: str
    facet_type: str | None
    vector: List[float]


@dataclass(slots=True)
class ChunkingResult:
    chunks: List[Chunk]
    metrics: ChunkMetrics
    index_documents: List[IndexedChunk]
    neighbor_merges: List[tuple[Chunk, Chunk]]
    facet_vectors: List[FacetVectorRecord] = field(default_factory=list)


class ChunkingPipeline:
    """Run semantic chunking with profile selection and facet generation."""

    def __init__(
        self,
        *,
        facet_generator: FacetGenerator | None = None,
        embedding_service: "EmbeddingService" | None = None,
        indexer: ChunkIndexer | None = None,
        embed_facets: bool = False,
    ) -> None:
        self._facet_generator = facet_generator or FacetGenerator()
        self._embedding_service = embedding_service
        self._indexer = indexer or ChunkIndexer()
        self._embed_facets = embed_facets

    def run(self, document: Document, *, profile: ChunkingProfile | None = None) -> ChunkingResult:
        profile = profile or select_profile(document)
        chunker = SemanticChunker(profile)
        chunks = chunker.chunk(document)
        for chunk in chunks:
            self._facet_generator.generate(chunk)
        facet_vectors: List[FacetVectorRecord] = []
        if self._embedding_service and chunks:
            facet_vectors = self._apply_embeddings(chunks)
        metrics = compute_metrics(chunks)
        index_documents: List[IndexedChunk] = []
        neighbor_merges: List[tuple[Chunk, Chunk]] = []
        if self._indexer:
            index_documents = self._indexer.build_documents(chunks)
            neighbor_merges = self._indexer.neighbor_merge(chunks)
            if (
                not neighbor_merges
                and len(chunks) > 1
                and all(chunk.embedding_qwen for chunk in chunks)
            ):
                neighbor_merges = [
                    (left, right)
                    for left, right in zip(chunks, chunks[1:])
                    if left.embedding_qwen and right.embedding_qwen
                ]
        return ChunkingResult(
            chunks=chunks,
            metrics=metrics,
            index_documents=index_documents,
            neighbor_merges=neighbor_merges,
            facet_vectors=facet_vectors,
        )

    def _apply_embeddings(self, chunks: List[Chunk]) -> List[FacetVectorRecord]:
        texts = [chunk.to_embedding_text() for chunk in chunks]
        sparse_inputs = [chunk.to_sparse_text() for chunk in chunks]
        dense_vectors, sparse_vectors = self._embedding_service.embed_texts(
            texts, sparse_texts=sparse_inputs
        )
        for chunk, dense, sparse in zip(chunks, dense_vectors, sparse_vectors):
            chunk.embedding_qwen = dense
            chunk.splade_terms = sparse
        if not self._embed_facets:
            return []
        payloads: list[tuple[Chunk, str]] = [
            (chunk, json.dumps(chunk.facet_json, sort_keys=True))
            for chunk in chunks
            if chunk.facet_json
        ]
        facet_records: List[FacetVectorRecord] = []
        if not payloads:
            return facet_records
        dense_vectors, _ = self._embedding_service.embed_texts([payload for _, payload in payloads])
        for (chunk, _), vector in zip(payloads, dense_vectors):
            chunk.facet_embedding_qwen = vector
            facet_records.append(
                FacetVectorRecord(
                    chunk_id=chunk.chunk_id,
                    doc_id=chunk.doc_id,
                    facet_type=chunk.facet_type,
                    vector=vector,
                )
            )
        return facet_records


__all__ = ["ChunkingPipeline", "ChunkingResult", "FacetVectorRecord"]
