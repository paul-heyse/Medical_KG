from __future__ import annotations

import pytest

from Medical_KG.catalog.models import Concept, ConceptFamily
from Medical_KG.embeddings import (
    EmbeddingService,
    GPURequirementError,
    GPUValidator,
    QwenEmbeddingClient,
    SPLADEExpander,
)


@pytest.fixture(autouse=True)
def reset_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REQUIRE_GPU", raising=False)


def test_gpu_validator_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REQUIRE_GPU", "0")
    validator = GPUValidator()
    validator.validate()  # does not raise


def test_gpu_validator_raises_without_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REQUIRE_GPU", "1")
    validator = GPUValidator()
    with pytest.raises(GPURequirementError):
        validator.validate()


def test_qwen_embeddings_are_deterministic() -> None:
    client = QwenEmbeddingClient(dimension=8, batch_size=4)
    first = client.embed(["hello world"])[0]
    second = client.embed(["hello world"])[0]
    assert pytest.approx(first) == second
    norm = sum(value * value for value in first) ** 0.5
    assert pytest.approx(norm, rel=1e-6) == 1.0


def test_embedding_service_sets_vectors(monkeypatch: pytest.MonkeyPatch) -> None:
    concept = Concept(
        iri="http://example.org/concept/1",
        ontology="TEST",
        family=ConceptFamily.CONDITION,
        label="Example concept",
        preferred_term="Example concept",
        definition="A sample concept for testing.",
        synonyms=[],
        codes={"test": "1"},
        xrefs={},
        parents=[],
        ancestors=[],
        attributes={"umls_cui": "C000"},
        release={"version": "1", "released_at": "2025-01-01"},
        license_bucket="open",
        provenance={"source": "unit"},
    )
    service = EmbeddingService(qwen=QwenEmbeddingClient(dimension=8, batch_size=4), splade=SPLADEExpander(top_k=4))
    service.embed_concepts([concept])
    assert concept.embedding_qwen is not None
    assert len(concept.embedding_qwen) == 8
    assert concept.splade_terms
