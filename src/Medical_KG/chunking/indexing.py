"""Utilities for producing multi-granularity index documents."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, List, Mapping, Sequence

from .chunker import Chunk


@dataclass(slots=True)
class IndexedChunk:
    """Representation of a chunk or aggregate suitable for indexing."""

    doc_id: str
    chunk_ids: List[str]
    granularity: str
    text: str
    tokens: int
    section: str | None
    title_path: str | None
    facet_json: Mapping[str, object] | None
    facet_type: str | None
    table_lines: List[str] | None
    embedding_qwen: List[float] | None
    splade_terms: Mapping[str, float] | None


class ChunkIndexer:
    """Generate multi-granularity index documents and neighbor merges."""

    paragraph_window: int = 512
    paragraph_overlap: float = 0.25

    def build_documents(self, chunks: Sequence[Chunk]) -> List[IndexedChunk]:
        documents: List[IndexedChunk] = []
        documents.extend(self._chunk_level(chunks))
        documents.extend(self._paragraph_level(chunks))
        documents.extend(self._section_level(chunks))
        return documents

    def neighbor_merge(
        self, chunks: Sequence[Chunk], *, min_cosine: float = 0.30
    ) -> List[tuple[Chunk, Chunk]]:
        """Return adjacent chunks whose embeddings are similar enough to merge at query time."""

        merges: List[tuple[Chunk, Chunk]] = []
        for left, right in zip(chunks, chunks[1:]):
            if not left.embedding_qwen or not right.embedding_qwen:
                continue
            score = self._cosine(left.embedding_qwen, right.embedding_qwen)
            if score >= min_cosine:
                merges.append((left, right))
        return merges

    def _chunk_level(self, chunks: Sequence[Chunk]) -> List[IndexedChunk]:
        documents: List[IndexedChunk] = []
        for chunk in chunks:
            documents.append(
                IndexedChunk(
                    doc_id=chunk.doc_id,
                    chunk_ids=[chunk.chunk_id],
                    granularity="chunk",
                    text=chunk.text,
                    tokens=chunk.tokens,
                    section=chunk.section,
                    title_path=chunk.title_path,
                    facet_json=chunk.facet_json,
                    facet_type=chunk.facet_type,
                    table_lines=chunk.table_lines,
                    embedding_qwen=chunk.embedding_qwen,
                    splade_terms=chunk.splade_terms or {},
                )
            )
        return documents

    def _paragraph_level(self, chunks: Sequence[Chunk]) -> List[IndexedChunk]:
        documents: List[IndexedChunk] = []
        window_tokens = self.paragraph_window
        overlap_tokens = int(window_tokens * self.paragraph_overlap)
        buffer: List[Chunk] = []
        token_sum = 0
        for chunk in chunks:
            buffer.append(chunk)
            token_sum += chunk.tokens
            if token_sum >= window_tokens:
                documents.append(self._aggregate(buffer, "paragraph"))
                while buffer and token_sum > overlap_tokens:
                    popped = buffer.pop(0)
                    token_sum -= popped.tokens
        if buffer:
            documents.append(self._aggregate(buffer, "paragraph"))
        return documents

    def _section_level(self, chunks: Sequence[Chunk]) -> List[IndexedChunk]:
        documents: List[IndexedChunk] = []
        current: List[Chunk] = []
        current_section: str | None = None
        for chunk in chunks:
            if chunk.section != current_section and current:
                documents.append(self._aggregate(current, "section"))
                current = []
            current.append(chunk)
            current_section = chunk.section
        if current:
            documents.append(self._aggregate(current, "section"))
        return documents

    def _aggregate(self, chunks: Sequence[Chunk], granularity: str) -> IndexedChunk:
        text = " ".join(chunk.text for chunk in chunks)
        tokens = sum(chunk.tokens for chunk in chunks)
        embeddings = [chunk.embedding_qwen for chunk in chunks if chunk.embedding_qwen]
        embedding = self._mean_pool(embeddings) if embeddings else None
        splade_terms: dict[str, float] = {}
        for chunk in chunks:
            for term, weight in (chunk.splade_terms or {}).items():
                splade_terms[term] = max(splade_terms.get(term, 0.0), weight)
        section = next((chunk.section for chunk in chunks if chunk.section), None)
        title_path = next((chunk.title_path for chunk in chunks if chunk.title_path), None)
        facet_json = next((chunk.facet_json for chunk in chunks if chunk.facet_json), None)
        facet_type = next((chunk.facet_type for chunk in chunks if chunk.facet_type), None)
        table_lines: List[str] | None = None
        for chunk in chunks:
            if chunk.table_lines:
                table_lines = (table_lines or []) + chunk.table_lines
        return IndexedChunk(
            doc_id=chunks[0].doc_id,
            chunk_ids=[chunk.chunk_id for chunk in chunks],
            granularity=granularity,
            text=text,
            tokens=tokens,
            section=section,
            title_path=title_path,
            facet_json=facet_json,
            facet_type=facet_type,
            table_lines=table_lines,
            embedding_qwen=embedding,
            splade_terms=splade_terms,
        )

    def _mean_pool(self, embeddings: Iterable[List[float]]) -> List[float]:
        vectors = list(embeddings)
        if not vectors:
            return []
        length = len(vectors[0])
        pooled = [0.0] * length
        for vector in vectors:
            for index, value in enumerate(vector):
                pooled[index] += value
        return [value / len(vectors) for value in pooled]

    def _cosine(self, a: Sequence[float], b: Sequence[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (norm_a * norm_b)


__all__ = ["ChunkIndexer", "IndexedChunk"]
