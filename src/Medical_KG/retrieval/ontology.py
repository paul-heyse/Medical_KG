"""Ontology-aware query expansion helpers."""
from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, MutableMapping
from dataclasses import dataclass


@dataclass(frozen=True)
class OntologyTerm:
    term: str
    weight: float


class ConceptCatalogClient:
    """Minimal interface for querying concept catalog synonyms."""

    def synonyms(self, identifier: str) -> Iterable[OntologyTerm]:  # pragma: no cover - interface
        raise NotImplementedError

    def search(self, text: str) -> Iterable[OntologyTerm]:  # pragma: no cover - interface
        raise NotImplementedError


class OntologyExpander:
    """Detects medical entities and adds deterministic synonyms to lexical queries."""

    _ID_PATTERN = re.compile(r"(nct\d{8}|rx[c]?ui:?\s*\d{4,7}|loinc\s*\d{1,7}-\d)", re.IGNORECASE)

    def __init__(self, catalog: ConceptCatalogClient | None = None) -> None:
        self._catalog = catalog

    def expand(self, query: str) -> Mapping[str, float]:
        expansions: MutableMapping[str, float] = {}
        if not query:
            return expansions
        if self._catalog:
            for match in self._ID_PATTERN.finditer(query):
                identifier = match.group(1).strip()
                for synonym in self._catalog.synonyms(identifier):
                    expansions[synonym.term] = max(expansions.get(synonym.term, 0.0), synonym.weight)
        normalized = re.sub(r"[^a-z0-9\s]", " ", query.lower())
        tokens = {token for token in normalized.split() if len(token) > 3}
        if self._catalog:
            for token in tokens:
                for synonym in self._catalog.search(token):
                    expansions.setdefault(synonym.term, synonym.weight)
        return expansions


__all__ = ["OntologyExpander", "OntologyTerm", "ConceptCatalogClient"]
