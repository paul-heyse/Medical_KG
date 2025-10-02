import pytest

from Medical_KG.catalog import (
    VALIDATORS,
    CatalogBuildResult,
    ConceptCatalogBuilder,
    ConceptFamily,
    ConceptSchemaValidator,
    LicensePolicy,
    MONDOLoader,
    SnomedCTLoader,
)
from Medical_KG.embeddings import EmbeddingService, QwenEmbeddingClient, SPLADEExpander


@pytest.fixture()
def snomed_loader() -> SnomedCTLoader:
    records = [
        {
            "conceptId": "73211009",
            "fsn": "Diabetes mellitus (disorder)",
            "preferred": "Diabetes mellitus",
            "synonyms": ["Sugar diabetes"],
            "definition": "A disorder characterized by hyperglycemia.",
            "parents": ["237602007"],
            "ancestors": ["64572001"],
            "icd10": ["E11"],
            "active": True,
        },
        {
            "conceptId": "44054006",
            "fsn": "Diabetes mellitus type 2 (disorder)",
            "preferred": "Type 2 diabetes mellitus",
            "synonyms": ["Non-insulin-dependent diabetes mellitus"],
            "definition": "A type of diabetes mellitus.",
            "parents": ["73211009"],
            "ancestors": ["64572001"],
            "icd10": ["E11"],
            "active": True,
        },
    ]
    return SnomedCTLoader(records)


@pytest.fixture()
def mondo_loader() -> MONDOLoader:
    nodes = [
        {
            "id": "MONDO:0005148",
            "label": "diabetes mellitus",
            "synonyms": ["Diabetes"],
            "definition": "A metabolic disease.",
            "xrefs": {"snomed": ["73211009"]},
            "preferred": "Diabetes mellitus",
            "format": "json",
        }
    ]
    return MONDOLoader(nodes)


@pytest.fixture()
def embedding_service() -> EmbeddingService:
    return EmbeddingService(qwen=QwenEmbeddingClient(dimension=16, batch_size=16), splade=SPLADEExpander(top_k=8))


def test_concepts_validate_against_schema(snomed_loader: SnomedCTLoader) -> None:
    validator = ConceptSchemaValidator.create()
    concepts = list(snomed_loader.load())
    assert concepts
    for concept in concepts:
        validator.validate(concept)
        assert concept.family == ConceptFamily.CONDITION


def test_builder_deduplicates_and_creates_crosswalks(
    snomed_loader: SnomedCTLoader,
    mondo_loader: MONDOLoader,
    embedding_service: EmbeddingService,
) -> None:
    builder = ConceptCatalogBuilder([snomed_loader, mondo_loader], embedding_service=embedding_service)
    result = builder.build()
    assert isinstance(result, CatalogBuildResult)
    assert result.concepts
    diabetes = next(concept for concept in result.concepts if "Diabetes mellitus" in concept.label)
    assert diabetes.same_as
    assert any("mondo" in iri.lower() for iri in diabetes.same_as)
    assert diabetes.embedding_qwen is not None
    assert diabetes.splade_terms is not None
    assert result.synonym_catalog["SNOMED"]
    assert len(result.release_hash) == 64


def test_license_policy_skips_restricted_loader(
    snomed_loader: SnomedCTLoader,
    mondo_loader: MONDOLoader,
) -> None:
    policy = LicensePolicy(entitlements={"open": True, "permissive": True, "restricted": False, "proprietary": False})
    builder = ConceptCatalogBuilder([snomed_loader, mondo_loader], license_policy=policy)
    result = builder.build()
    assert all(concept.ontology != "SNOMED" for concept in result.concepts)
    assert result.audit_log.entries
    skipped = next(entry for entry in result.audit_log.entries if entry["action"] == "loader.skipped")
    assert skipped["resource"] == "SNOMED"


def test_identifier_validators() -> None:
    assert VALIDATORS["nct"]("NCT01234567")
    assert VALIDATORS["pmid"]("123456")
    assert VALIDATORS["doi"]("10.1000/xyz123")
    assert VALIDATORS["loinc"]("1234-5")
    assert VALIDATORS["gtin14"]("01234567890128")
    assert VALIDATORS["unii"]("ABCDEF1234")
    assert VALIDATORS["snomed"]("1234567") is False
