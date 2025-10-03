"""Neo4j helpers for persisting chunk nodes and relationships."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Protocol, Sequence

from .chunker import Chunk


class Neo4jSession(Protocol):  # pragma: no cover
    def run(self, query: str, parameters: Mapping[str, object] | None = None) -> None: ...


@dataclass(slots=True)
class ChunkGraphWriter:
    """Create :Chunk nodes, relationships, and vector index in Neo4j."""

    session: Neo4jSession
    vector_index_name: str = "chunk_qwen_idx"
    vector_dimension: int = 4096
    similarity_metric: str = "cosine"
    similarity_model: str = "qwen3-embedding-8b"
    similarity_version: str = "1"
    _vector_index_created: bool = False

    def sync(
        self,
        document_id: str,
        chunks: Sequence[Chunk],
        *,
        neighbor_merges: Sequence[tuple[Chunk, Chunk]] | None = None,
    ) -> None:
        for index, chunk in enumerate(chunks):
            self._upsert_chunk(chunk)
            self._link_document(document_id, chunk.chunk_id, index)
            self._link_overlap(chunk)
        self.ensure_vector_index()
        if neighbor_merges:
            self._link_similar(neighbor_merges)

    def _upsert_chunk(self, chunk: Chunk) -> None:
        query = "MERGE (c:Chunk {id: $id}) " "SET c += $props"
        props = {
            "doc_id": chunk.doc_id,
            "text": chunk.text,
            "type": chunk.intent.value,
            "section": chunk.section,
            "title_path": chunk.title_path,
            "tokens": chunk.tokens,
            "start_char": chunk.start,
            "end_char": chunk.end,
            "section_loinc": chunk.section_loinc,
            "facet_json": chunk.facet_json,
            "facet_type": chunk.facet_type,
            "embedding_qwen": chunk.embedding_qwen,
            "splade_terms": chunk.splade_terms,
            "table_digest": chunk.table_digest,
            "table_lines": chunk.table_lines,
            "coherence_score": chunk.coherence_score,
            "createdAt": chunk.created_at.isoformat(),
        }
        self.session.run(query, {"id": chunk.chunk_id, "props": props})

    def _link_document(self, document_id: str, chunk_id: str, index: int) -> None:
        query = (
            "MERGE (d:Document {id: $doc_id}) "
            "MERGE (c:Chunk {id: $chunk_id}) "
            "MERGE (d)-[r:HAS_CHUNK]->(c) "
            "SET r.index = $index"
        )
        params = {"doc_id": document_id, "chunk_id": chunk_id, "index": index}
        self.session.run(query, params)

    def _link_overlap(self, chunk: Chunk) -> None:
        if not chunk.overlap_with_prev:
            return
        previous_id = chunk.overlap_with_prev.get("chunk_id")
        if not previous_id:
            return
        start = chunk.overlap_with_prev.get("start")
        end = chunk.overlap_with_prev.get("end")
        tokens = chunk.overlap_with_prev.get("token_window")
        query = (
            "MATCH (prev:Chunk {id: $prev_id}), (curr:Chunk {id: $curr_id}) "
            "MERGE (prev)-[r:OVERLAPS]->(curr) "
            "SET r.start = $start, r.end = $end, r.token_window = $tokens"
        )
        params = {
            "prev_id": previous_id,
            "curr_id": chunk.chunk_id,
            "start": start,
            "end": end,
            "tokens": tokens,
        }
        self.session.run(query, params)

    def ensure_vector_index(self) -> None:
        if self._vector_index_created:
            return
        query = "CALL db.index.vector.createNodeIndex($name, 'Chunk', 'embedding_qwen', $dimension, $metric)"
        params = {
            "name": self.vector_index_name,
            "dimension": self.vector_dimension,
            "metric": self.similarity_metric,
        }
        self.session.run(query, params)
        self._vector_index_created = True

    def _link_similar(self, merges: Sequence[tuple[Chunk, Chunk]]) -> None:
        for left, right in merges:
            if not left.embedding_qwen or not right.embedding_qwen:
                continue
            score = self._cosine(left.embedding_qwen, right.embedding_qwen)
            query = (
                "MATCH (a:Chunk {id: $left}), (b:Chunk {id: $right}) "
                "MERGE (a)-[r:SIMILAR_TO]->(b) "
                "SET r.score = $score, r.model = $model, r.version = $version"
            )
            params = {
                "left": left.chunk_id,
                "right": right.chunk_id,
                "score": score,
                "model": self.similarity_model,
                "version": self.similarity_version,
            }
            self.session.run(query, params)
            inverse = (
                "MATCH (a:Chunk {id: $left}), (b:Chunk {id: $right}) "
                "MERGE (b)-[r:SIMILAR_TO]->(a) "
                "SET r.score = $score, r.model = $model, r.version = $version"
            )
            self.session.run(inverse, params)

    def _cosine(self, left: Sequence[float], right: Sequence[float]) -> float:
        dot = sum(a * b for a, b in zip(left, right))
        norm_left = math.sqrt(sum(a * a for a in left)) or 1.0
        norm_right = math.sqrt(sum(b * b for b in right)) or 1.0
        return dot / (norm_left * norm_right)


__all__ = ["ChunkGraphWriter", "Neo4jSession"]
