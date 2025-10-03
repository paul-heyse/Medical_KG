from __future__ import annotations

from typing import Iterable

from Medical_KG.catalog.loaders import ConceptLoader
from Medical_KG.catalog.models import Concept, ConceptFamily, SynonymType
from Medical_KG.catalog.pipeline import ConceptCatalogBuilder, LicensePolicy
from Medical_KG.catalog.state import CatalogStateStore


class DummyLoader(ConceptLoader):
    ontology = "DUMMY"
    family = ConceptFamily.CONDITION
    license_bucket = "open"

    def __init__(self) -> None:
        super().__init__(release_version="2025-01")

    def load(self) -> Iterable[Concept]:
        yield self._build(
            iri="https://example.org/dummy/1",
            label="Condition A",
            preferred_term="Condition A",
            definition="Definition",
            synonyms=[("Alpha", SynonymType.RELATED)],
            codes={"dummy": "1"},
            attributes={"umls_cui": "C123"},
        )
        yield self._build(
            iri="https://example.org/dummy/2",
            label="Condition A",
            preferred_term="Condition A",
            definition="Definition",
            synonyms=[("Beta", SynonymType.RELATED)],
            codes={"dummy": "2"},
            attributes={"umls_cui": "C123"},
            xrefs={"icd10": ["I10"]},
        )


class RecordingEmbeddingService:
    def __init__(self) -> None:
        self.calls = 0

    def embed_concepts(self, concepts) -> None:
        self.calls += 1
        for index, concept in enumerate(concepts):
            concept.embedding_qwen = [float(index)]


def test_catalog_builder_deduplication_and_crosswalk() -> None:
    loader = DummyLoader()
    embedding_service = RecordingEmbeddingService()
    state_store = CatalogStateStore()
    builder = ConceptCatalogBuilder(
        [loader],
        license_policy=LicensePolicy.permissive(),
        embedding_service=embedding_service,
        state_store=state_store,
    )

    result = builder.build()

    assert len(result.concepts) == 1
    concept = result.concepts[0]
    assert set(syn.value for syn in concept.synonyms) == {"alpha", "beta"}
    assert "https://example.org/dummy/2" in concept.same_as
    assert result.changed_ontologies == {"DUMMY"}
    assert embedding_service.calls == 1
    assert result.release_versions["DUMMY"] == "2025-01"
    assert "DUMMY" in result.synonym_catalog
    assert not result.skipped
    assert state_store.get_release_hash() == result.release_hash

    second_run = builder.build()
    assert second_run.skipped
    assert not second_run.changed_ontologies
    assert embedding_service.calls == 1
