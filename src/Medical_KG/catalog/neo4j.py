"""Neo4j synchronisation helpers for the concept catalog."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Protocol, cast

from .models import Concept
from .pipeline import CatalogBuildResult
from .types import JsonValue


class Neo4jSession(Protocol):  # pragma: no cover - interface definition
    def run(self, query: str, parameters: Mapping[str, JsonValue] | None = None) -> None:
        """Execute a Cypher query."""


@dataclass(slots=True)
class ConceptGraphWriter:
    """Generate Cypher statements to upsert concepts and relationships."""

    session: Neo4jSession
    constraint_name: str = "concept_iri_unique"
    vector_index_name: str = "concept_qwen_idx"
    vector_dimension: int = 4096
    similarity_metric: str = "cosine"
    _constraint_created: bool = False
    _vector_index_created: bool = False

    def sync(self, result: CatalogBuildResult) -> None:
        if result.skipped:
            return
        self.ensure_constraint()
        for concept in result.concepts:
            self._upsert_concept(concept)
        self._create_relationships(result.concepts)
        self.ensure_vector_index()

    def ensure_constraint(self) -> None:
        if self._constraint_created:
            return
        query = "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Concept) REQUIRE c.iri IS UNIQUE"
        self.session.run(query)
        self._constraint_created = True

    def ensure_vector_index(self) -> None:
        if self._vector_index_created:
            return
        query = "CALL db.index.vector.createNodeIndex($name, 'Concept', 'embedding_qwen', $dimension, $metric)"
        params = {
            "name": self.vector_index_name,
            "dimension": self.vector_dimension,
            "metric": self.similarity_metric,
        }
        self.session.run(query, params)
        self._vector_index_created = True

    def _upsert_concept(self, concept: Concept) -> None:
        family_label = concept.family.name.title().replace("_", "")
        query = f"MERGE (c:Concept:{family_label} {{iri: $iri}}) " "SET c += $props"
        props: dict[str, JsonValue] = {
            "ontology": concept.ontology,
            "family": concept.family.value,
            "label": concept.label,
            "preferred_term": concept.preferred_term,
            "definition": concept.definition,
            "synonyms": [syn.value for syn in concept.synonyms],
            "codes": concept.codes,
            "xrefs": concept.xrefs,
            "release": concept.release,
            "license_bucket": concept.license_bucket,
            "provenance": concept.provenance,
            "embedding_qwen": concept.embedding_qwen,
            "splade_terms": concept.splade_terms,
        }
        parameters: dict[str, JsonValue] = {
            "iri": concept.iri,
            "props": cast(Mapping[str, JsonValue], props),
        }
        self.session.run(query, cast(Mapping[str, JsonValue], parameters))

    def _create_relationships(self, concepts: Iterable[Concept]) -> None:
        for concept in concepts:
            for parent in concept.parents:
                self._merge_relationship("IS_A", concept.iri, parent)
            for equivalent in concept.same_as:
                if equivalent == concept.iri:
                    continue
                self._merge_relationship("SAME_AS", concept.iri, equivalent)

    def _merge_relationship(self, rel_type: str, start: str, end: str) -> None:
        query = (
            "MATCH (a:Concept {iri: $start}), (b:Concept {iri: $end}) "
            f"MERGE (a)-[:{rel_type}]->(b)"
        )
        self.session.run(query, {"start": start, "end": end})


__all__ = ["ConceptGraphWriter", "Neo4jSession"]
