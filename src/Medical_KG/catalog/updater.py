"""Scheduling helpers for refreshing the concept catalog."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .neo4j import ConceptGraphWriter
from .opensearch import ConceptIndexManager
from .pipeline import CatalogAuditLog, CatalogBuildResult, ConceptCatalogBuilder
from .state import CatalogStateStore


def _default_schedule() -> dict[str, timedelta]:
    return {
        "SNOMED": timedelta(days=90),
        "ICD11": timedelta(days=182),
        "MONDO": timedelta(days=30),
        "HPO": timedelta(days=30),
        "RXNORM": timedelta(days=7),
        "GUDID": timedelta(hours=6),
    }


@dataclass(slots=True)
class CatalogUpdater:
    """Coordinate periodic rebuilds and downstream indexing."""

    builder: ConceptCatalogBuilder
    graph_writer: ConceptGraphWriter
    index_manager: ConceptIndexManager
    state_store: CatalogStateStore
    schedule: Mapping[str, timedelta] = field(default_factory=_default_schedule)
    last_run: dict[str, datetime] = field(default_factory=dict)

    def is_due(self, ontology: str, *, when: datetime | None = None) -> bool:
        when = when or datetime.utcnow()
        last = self.last_run.get(ontology.upper())
        if last is None:
            return True
        interval = self.schedule.get(ontology.upper(), timedelta(days=30))
        return when - last >= interval

    def refresh(self, *, force: bool = False, when: datetime | None = None) -> CatalogBuildResult:
        when = when or datetime.utcnow()
        due = {ontology for ontology in self.schedule if self.is_due(ontology, when=when)}
        if not due and not force:
            return CatalogBuildResult(
                concepts=[],
                release_hash=self.state_store.get_release_hash() or "",
                synonym_catalog={},
                audit_log=CatalogAuditLog(),
                release_versions=self.state_store.get_release_versions(),
                changed_ontologies=set(),
                skipped=True,
            )
        result = self.builder.build()
        if result.skipped:
            return result
        target_ontologies = result.changed_ontologies or set(result.release_versions)
        if not target_ontologies:
            return result
        self.index_manager.ensure_index(result.synonym_catalog)
        concepts_to_index = [
            concept for concept in result.concepts if concept.ontology in target_ontologies
        ]
        self.index_manager.index_concepts(concepts_to_index)
        self.index_manager.reload_analyzers()
        self.graph_writer.sync(result)
        for ontology in target_ontologies:
            self.last_run[ontology.upper()] = when
        self.state_store.set_release_hash(result.release_hash)
        self.state_store.set_release_versions(result.release_versions)
        return result


__all__ = ["CatalogUpdater"]
