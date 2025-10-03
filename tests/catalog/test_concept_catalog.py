from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from Medical_KG.catalog import (
    VALIDATORS,
    CatalogBuildResult,
    CatalogStateStore,
    CatalogUpdater,
    ConceptCatalogBuilder,
    ConceptFamily,
    ConceptGraphWriter,
    ConceptIndexManager,
    ConceptSchemaValidator,
    LicensePolicy,
    MONDOLoader,
    SnomedCTLoader,
    load_license_policy,
)
from Medical_KG.catalog.types import JsonValue
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
    return EmbeddingService(
        qwen=QwenEmbeddingClient(dimension=16, batch_size=16),
        splade=SPLADEExpander(top_k=8, batch_size=8),
    )


@pytest.fixture()
def state_store() -> CatalogStateStore:
    return CatalogStateStore()


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
    state_store: CatalogStateStore,
) -> None:
    builder = ConceptCatalogBuilder(
        [snomed_loader, mondo_loader],
        embedding_service=embedding_service,
        state_store=state_store,
    )
    result = builder.build()
    assert isinstance(result, CatalogBuildResult)
    assert result.concepts
    diabetes = next(concept for concept in result.concepts if "Diabetes mellitus" in concept.label)
    assert diabetes.same_as
    assert any("mondo" in iri.lower() for iri in diabetes.same_as)
    assert diabetes.embedding_qwen is not None
    assert diabetes.splade_terms is not None
    assert all(isinstance(entry, list) for entry in result.synonym_catalog.values())
    assert result.synonym_catalog["SNOMED"]
    assert len(result.release_hash) == 64
    assert not result.skipped
    assert result.changed_ontologies
    payloads = result.audit_log.as_payloads()
    assert payloads
    assert all(isinstance(entry["resource"], str) for entry in payloads)


def test_license_policy_skips_restricted_loader(
    snomed_loader: SnomedCTLoader,
    mondo_loader: MONDOLoader,
) -> None:
    policy = LicensePolicy(
        entitlements={"open": True, "permissive": True, "restricted": False, "proprietary": False}
    )
    builder = ConceptCatalogBuilder([snomed_loader, mondo_loader], license_policy=policy)
    result = builder.build()
    assert all(concept.ontology != "SNOMED" for concept in result.concepts)
    assert result.audit_log.entries
    skipped = next(entry for entry in result.audit_log.entries if entry.action == "loader.skipped")
    assert skipped.resource == "SNOMED"
    assert skipped.metadata == {"reason": "license", "license_bucket": "restricted"}


def test_license_policy_from_file(tmp_path: Path) -> None:
    config = tmp_path / "licenses.yml"
    config.write_text(
        """
        buckets:
          restricted: false
          proprietary: false
        loaders:
          SNOMED:
            enabled: false
        """
    )
    policy = load_license_policy(config)

    class DummyLoader:
        ontology = "SNOMED"
        license_bucket = "restricted"

    assert policy.is_loader_enabled(DummyLoader()) is False


def test_identifier_validators() -> None:
    assert VALIDATORS["nct"]("NCT01234567")
    assert VALIDATORS["pmid"]("123456")
    assert VALIDATORS["doi"]("10.1000/xyz123")
    assert VALIDATORS["loinc"]("1234-5")
    assert VALIDATORS["gtin14"]("01234567890128")
    assert VALIDATORS["unii"]("ABCDEF1234")
    assert VALIDATORS["snomed"]("1234567") is False


def test_catalog_state_store_idempotency(
    snomed_loader: SnomedCTLoader,
    mondo_loader: MONDOLoader,
    embedding_service: EmbeddingService,
    state_store: CatalogStateStore,
) -> None:
    builder = ConceptCatalogBuilder(
        [snomed_loader, mondo_loader],
        embedding_service=embedding_service,
        state_store=state_store,
    )
    first = builder.build()
    assert not first.skipped
    second = builder.build()
    assert second.skipped


class FakeSession:
    def __init__(self) -> None:
        self.queries: list[tuple[str, dict[str, JsonValue]]] = []

    def run(self, query: str, parameters: Mapping[str, JsonValue] | None = None) -> None:
        payload = dict(parameters or {})
        if "props" in payload:
            props = payload["props"]
            assert isinstance(props, dict)
            assert all(isinstance(key, str) for key in props)
        self.queries.append((query, payload))


class FakeIndices:
    def __init__(self) -> None:
        self.created: list[dict[str, JsonValue]] = []
        self.updated: list[dict[str, JsonValue]] = []
        self.reloads: int = 0
        self._exists = False

    def exists(self, index: str) -> bool:
        return self._exists

    def create(self, index: str, body: Mapping[str, JsonValue]) -> None:
        self._exists = True
        assert isinstance(index, str)
        self.created.append({"index": index, "body": dict(body)})

    def put_settings(self, index: str, body: Mapping[str, JsonValue]) -> None:
        assert "analysis" in body
        self.updated.append({"index": index, "body": dict(body)})

    def reload_search_analyzers(self, index: str) -> None:
        self.reloads += 1


class FakeOpenSearchClient:
    def __init__(self) -> None:
        self.indices = FakeIndices()
        self.bulk_operations: list[list[Mapping[str, JsonValue]]] = []

    def bulk(self, operations: Sequence[Mapping[str, JsonValue]]) -> Mapping[str, JsonValue]:
        formatted = list(operations)
        assert formatted, "bulk operations must not be empty"
        for op in formatted:
            assert all(isinstance(key, str) for key in op)
        self.bulk_operations.append(formatted)
        return {"errors": False}


def test_concept_graph_writer_creates_nodes(
    snomed_loader: SnomedCTLoader,
    embedding_service: EmbeddingService,
    state_store: CatalogStateStore,
) -> None:
    builder = ConceptCatalogBuilder(
        [snomed_loader], embedding_service=embedding_service, state_store=state_store
    )
    result = builder.build()
    session = FakeSession()
    writer = ConceptGraphWriter(session)
    writer.sync(result)
    assert any("MERGE (c:Concept" in query for query, _ in session.queries)
    assert any("CALL db.index.vector.createNodeIndex" in query for query, _ in session.queries)


def test_concept_index_manager_indexes_documents(
    snomed_loader: SnomedCTLoader,
    embedding_service: EmbeddingService,
    state_store: CatalogStateStore,
) -> None:
    builder = ConceptCatalogBuilder(
        [snomed_loader], embedding_service=embedding_service, state_store=state_store
    )
    result = builder.build()
    client = FakeOpenSearchClient()
    manager = ConceptIndexManager(client)
    manager.ensure_index(result.synonym_catalog)
    manager.index_concepts(result.concepts)
    query = manager.build_search_query("diabetes")
    assert client.indices.created
    assert client.bulk_operations
    assert "multi_match" in query["query"]
    operations = client.bulk_operations[0]
    assert isinstance(operations[0], dict)
    document = operations[1]
    assert isinstance(document["synonyms"], list)
    assert all("value" in entry for entry in document["synonyms"])


def test_catalog_updater_refreshes_changed_ontologies(
    snomed_loader: SnomedCTLoader,
    mondo_loader: MONDOLoader,
    embedding_service: EmbeddingService,
    state_store: CatalogStateStore,
) -> None:
    builder = ConceptCatalogBuilder(
        [snomed_loader, mondo_loader],
        embedding_service=embedding_service,
        state_store=state_store,
    )
    session = FakeSession()
    writer = ConceptGraphWriter(session)
    client = FakeOpenSearchClient()
    manager = ConceptIndexManager(client)
    updater = CatalogUpdater(
        builder=builder, graph_writer=writer, index_manager=manager, state_store=state_store
    )
    result = updater.refresh(force=True)
    assert result.changed_ontologies
    assert session.queries
    assert client.bulk_operations
    skipped = updater.refresh()
    assert skipped.skipped
