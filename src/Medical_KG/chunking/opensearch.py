"""OpenSearch index management for semantic chunks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, MutableSequence, Protocol, Sequence

from .chunker import Chunk
from .indexing import IndexedChunk
from .pipeline import FacetVectorRecord


class OpenSearchIndices(Protocol):  # pragma: no cover
    def exists(self, index: str) -> bool: ...

    def create(self, index: str, body: Mapping[str, object]) -> None: ...

    def reload_search_analyzers(self, index: str) -> None: ...


class OpenSearchClient(Protocol):  # pragma: no cover
    @property
    def indices(self) -> OpenSearchIndices: ...

    def bulk(self, operations: Sequence[Mapping[str, object]]) -> Mapping[str, object]: ...


@dataclass(slots=True)
class ChunkSearchIndexer:
    """Create and populate the chunks_v1 OpenSearch index."""

    client: OpenSearchClient
    index_name: str = "chunks_v1"
    field_boosts: Mapping[str, float] = field(
        default_factory=lambda: {
            "title_path": 2.0,
            "facet_json": 1.6,
            "table_lines": 1.2,
            "body": 1.0,
        }
    )

    def ensure_index(self) -> None:
        if self.client.indices.exists(self.index_name):
            return
        body = {
            "settings": {
                "similarity": {"default": {"type": "BM25"}},
                "analysis": {
                    "analyzer": {"chunk_bm25": {"tokenizer": "standard", "filter": ["lowercase"]}}
                }
            },
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "doc_id": {"type": "keyword"},
                    "body": {"type": "text", "analyzer": "chunk_bm25"},
                    "title_path": {"type": "text", "analyzer": "chunk_bm25"},
                    "facet_json": {"type": "text", "analyzer": "chunk_bm25"},
                    "facet_type": {"type": "keyword"},
                    "granularity": {"type": "keyword"},
                    "tokens": {"type": "integer"},
                    "table_lines": {"type": "text", "analyzer": "chunk_bm25"},
                    "embedding_qwen": {
                        "type": "dense_vector",
                        "dims": 4096,
                        "index": True,
                        "similarity": "cosine",
                    },
                    "splade_terms": {"type": "rank_features"},
                }
            },
        }
        self.client.indices.create(index=self.index_name, body=body)

    def index_chunks(
        self, base_chunks: Sequence[Chunk], multi_gran: Iterable[IndexedChunk]
    ) -> None:
        operations: MutableSequence[Mapping[str, object]] = []
        for chunk in base_chunks:
            operations.append({"index": {"_index": self.index_name, "_id": chunk.chunk_id}})
            operations.append(self._serialise_chunk(chunk, granularity="chunk"))
        for aggregate in multi_gran:
            doc_id = "::".join(aggregate.chunk_ids)
            operations.append({"index": {"_index": self.index_name, "_id": doc_id}})
            operations.append(
                {
                    "id": doc_id,
                    "doc_id": aggregate.doc_id,
                    "body": aggregate.text,
                    "title_path": aggregate.title_path,
                    "facet_json": self._serialize_facet(aggregate.facet_json),
                    "facet_type": aggregate.facet_type,
                    "granularity": aggregate.granularity,
                    "tokens": aggregate.tokens,
                    "table_lines": self._combine_table_lines(aggregate.table_lines),
                    "embedding_qwen": aggregate.embedding_qwen,
                    "splade_terms": aggregate.splade_terms,
                }
            )
        if operations:
            self.client.bulk(operations)
            self.client.indices.reload_search_analyzers(index=self.index_name)

    def build_query(self, text: str) -> Mapping[str, object]:
        fields = [f"{name}^{boost}" for name, boost in self.field_boosts.items()]
        return {
            "query": {
                "bool": {
                    "should": [
                        {"multi_match": {"query": text, "fields": fields}},
                        {"match": {"granularity": "paragraph"}},
                    ]
                }
            }
        }

    def _serialise_chunk(self, chunk: Chunk, *, granularity: str) -> Mapping[str, object]:
        return {
            "id": chunk.chunk_id,
            "doc_id": chunk.doc_id,
            "body": chunk.text,
            "title_path": chunk.title_path,
            "facet_json": self._serialize_facet(chunk.facet_json),
            "facet_type": chunk.facet_type,
            "granularity": granularity,
            "tokens": chunk.tokens,
            "table_lines": self._combine_table_lines(chunk.table_lines),
            "embedding_qwen": chunk.embedding_qwen,
            "splade_terms": chunk.splade_terms or {},
        }

    def _serialize_facet(self, payload: Mapping[str, object] | None) -> str | None:
        if not payload:
            return None
        try:
            import json

            return json.dumps(payload, sort_keys=True)
        except (TypeError, ValueError):
            return str(payload)

    def _combine_table_lines(self, lines: Sequence[str] | None) -> str | None:
        if not lines:
            return None
        return "\n".join(lines)



@dataclass(slots=True)
class FacetVectorIndexer:
    """Manage optional facet vector index for facet embeddings."""

    client: OpenSearchClient
    index_name: str = "facets_v1"

    def ensure_index(self, *, dims: int = 4096) -> None:
        if self.client.indices.exists(self.index_name):
            return
        body = {
            "mappings": {
                "properties": {
                    "id": {"type": "keyword"},
                    "chunk_id": {"type": "keyword"},
                    "doc_id": {"type": "keyword"},
                    "facet_type": {"type": "keyword"},
                    "embedding_qwen": {
                        "type": "dense_vector",
                        "dims": dims,
                        "index": True,
                        "similarity": "cosine",
                    },
                }
            }
        }
        self.client.indices.create(index=self.index_name, body=body)

    def index_vectors(self, records: Sequence[FacetVectorRecord]) -> None:
        if not records:
            return
        dims = len(records[0].vector) if records[0].vector else 0
        self.ensure_index(dims=dims or 4096)
        ops: MutableSequence[Mapping[str, object]] = []
        for record in records:
            doc_id = f"{record.chunk_id}:{record.facet_type or 'facet'}"
            ops.append({"index": {"_index": self.index_name, "_id": doc_id}})
            ops.append(
                {
                    "id": doc_id,
                    "chunk_id": record.chunk_id,
                    "doc_id": record.doc_id,
                    "facet_type": record.facet_type,
                    "embedding_qwen": record.vector,
                }
            )
        self.client.bulk(ops)


__all__ = ["ChunkSearchIndexer", "FacetVectorIndexer", "OpenSearchClient"]
