"""OpenSearch index management for concept catalog documents."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, MutableSequence, Sequence
from dataclasses import dataclass
from typing import Protocol

from .models import Concept
from .types import JsonValue


class OpenSearchIndices(Protocol):  # pragma: no cover - interface definition
    def exists(self, index: str) -> bool: ...

    def create(self, index: str, body: Mapping[str, JsonValue]) -> None: ...

    def put_settings(self, index: str, body: Mapping[str, JsonValue]) -> None: ...

    def reload_search_analyzers(self, index: str) -> None: ...


class OpenSearchClient(Protocol):  # pragma: no cover - interface definition
    @property
    def indices(self) -> OpenSearchIndices: ...

    def bulk(self, operations: Sequence[Mapping[str, JsonValue]]) -> Mapping[str, JsonValue]: ...


@dataclass(slots=True)
class ConceptIndexManager:
    """Manage the concepts_v1 OpenSearch index and bulk ingestion."""

    client: OpenSearchClient
    index_name: str = "concepts_v1"
    synonym_filter_name: str = "biomed_synonyms"
    analyzer_name: str = "biomed"

    def ensure_index(self, synonym_catalog: Mapping[str, Iterable[str]]) -> None:
        if not self.client.indices.exists(self.index_name):
            body = self._index_body(synonym_catalog)
            self.client.indices.create(index=self.index_name, body=body)
        else:
            self.update_synonyms(synonym_catalog)

    def update_synonyms(self, synonym_catalog: Mapping[str, Iterable[str]]) -> None:
        synonyms = self._format_synonyms(synonym_catalog)
        settings = {
            "analysis": {
                "filter": {
                    self.synonym_filter_name: {
                        "type": "synonym_graph",
                        "synonyms": synonyms,
                    }
                }
            }
        }
        self.client.indices.put_settings(index=self.index_name, body=settings)

    def reload_analyzers(self) -> None:
        self.client.indices.reload_search_analyzers(index=self.index_name)

    def index_concepts(self, concepts: Sequence[Concept]) -> None:
        operations: MutableSequence[Mapping[str, JsonValue]] = []
        for concept in concepts:
            operations.append({"index": {"_index": self.index_name, "_id": concept.iri}})
            operations.append(self._serialise_concept(concept))
        if operations:
            self.client.bulk(operations)

    def build_search_query(self, text: str) -> Mapping[str, JsonValue]:
        return {
            "query": {
                "multi_match": {
                    "query": text,
                    "fields": ["label^3", "synonyms.value^2", "definition^0.5"],
                }
            }
        }

    def _index_body(self, synonym_catalog: Mapping[str, Iterable[str]]) -> Mapping[str, JsonValue]:
        return {
            "settings": {
                "analysis": {
                    "analyzer": {
                        self.analyzer_name: {
                            "tokenizer": "standard",
                            "filter": ["lowercase", self.synonym_filter_name],
                        }
                    },
                    "filter": {
                        self.synonym_filter_name: {
                            "type": "synonym_graph",
                            "synonyms_path": "analysis/biomed_synonyms.txt",
                        }
                    },
                }
            },
            "mappings": {
                "properties": {
                    "iri": {"type": "keyword"},
                    "family": {"type": "keyword"},
                    "ontology": {"type": "keyword"},
                    "label": {"type": "text", "analyzer": self.analyzer_name},
                    "preferred_term": {"type": "text", "analyzer": self.analyzer_name},
                    "definition": {"type": "text", "analyzer": self.analyzer_name},
                    "synonyms": {
                        "type": "nested",
                        "properties": {
                            "value": {"type": "text", "analyzer": self.analyzer_name},
                            "type": {"type": "keyword"},
                        },
                    },
                    "codes": {
                        "type": "nested",
                        "properties": {
                            "system": {"type": "keyword"},
                            "code": {"type": "keyword"},
                        },
                    },
                    "splade_terms": {"type": "rank_features"},
                    "embedding_qwen": {
                        "type": "dense_vector",
                        "dims": 4096,
                        "index": True,
                        "similarity": "cosine",
                    },
                }
            },
        }

    def _serialise_concept(self, concept: Concept) -> Mapping[str, JsonValue]:
        return {
            "iri": concept.iri,
            "ontology": concept.ontology,
            "family": concept.family.value,
            "label": concept.label,
            "preferred_term": concept.preferred_term,
            "definition": concept.definition,
            "synonyms": [
                {"value": synonym.value, "type": synonym.type.value} for synonym in concept.synonyms
            ],
            "codes": [{"system": system, "code": code} for system, code in concept.codes.items()],
            "splade_terms": concept.splade_terms or {},
            "embedding_qwen": concept.embedding_qwen,
            "license_bucket": concept.license_bucket,
            "release": concept.release,
        }

    def _format_synonyms(self, synonym_catalog: Mapping[str, Iterable[str]]) -> list[str]:
        lines: list[str] = []
        for synonyms in synonym_catalog.values():
            unique = sorted({syn.lower() for syn in synonyms if syn})
            if len(unique) < 2:
                continue
            lines.append(", ".join(unique))
        return lines


__all__ = ["ConceptIndexManager", "OpenSearchClient"]
