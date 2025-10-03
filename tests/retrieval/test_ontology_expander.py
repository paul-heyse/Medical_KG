from __future__ import annotations

from dataclasses import dataclass

import pytest

from Medical_KG.retrieval.ontology import ConceptCatalogClient, OntologyExpander, OntologyTerm


@dataclass
class StubCatalog(ConceptCatalogClient):
    synonyms_map: dict[str, list[OntologyTerm]]
    search_map: dict[str, list[OntologyTerm]]

    def synonyms(
        self, identifier: str
    ) -> list[OntologyTerm]:  # pragma: no cover - executed in tests
        return list(self.synonyms_map.get(identifier, ()))

    def search(self, text: str) -> list[OntologyTerm]:  # pragma: no cover - executed in tests
        return list(self.search_map.get(text, ()))


def test_synonym_expansion_for_identifiers() -> None:
    catalog = StubCatalog(
        synonyms_map={"NCT12345678": [OntologyTerm(term="KEYTRUDA", weight=1.0)]},
        search_map={},
    )
    expander = OntologyExpander(catalog)
    expanded = expander.expand("Trial NCT12345678 for pembrolizumab")
    assert expanded["KEYTRUDA"] == pytest.approx(1.0)


def test_token_expansion_for_terms() -> None:
    catalog = StubCatalog(
        synonyms_map={},
        search_map={"egfr": [OntologyTerm(term="epidermal growth factor receptor", weight=0.9)]},
    )
    expander = OntologyExpander(catalog)
    expanded = expander.expand("EGFR signaling pathways")
    assert "epidermal growth factor receptor" in expanded


def test_empty_query_returns_empty_mapping() -> None:
    expander = OntologyExpander()
    assert expander.expand("") == {}


def test_hypernym_like_expansion() -> None:
    catalog = StubCatalog(
        synonyms_map={},
        search_map={
            "lung": [OntologyTerm(term="pulmonary", weight=0.6)],
            "cancer": [OntologyTerm(term="neoplasm", weight=0.8)],
        },
    )
    expander = OntologyExpander(catalog)
    expanded = expander.expand("lung cancer treatment")
    assert "neoplasm" in expanded
    assert expanded["neoplasm"] == pytest.approx(0.8)
