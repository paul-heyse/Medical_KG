from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

import pytest

from Medical_KG.embeddings.gpu import GPUValidator
from Medical_KG.embeddings.service import EmbeddingMetrics, EmbeddingService


class FakeQwen:
    def __init__(self) -> None:
        self.calls: list[Sequence[str]] = []

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        self.calls.append(texts)
        return [[float(len(text)) for _ in range(2)] for text in texts]


class FakeSplade:
    def __init__(self) -> None:
        self.calls: list[Sequence[str]] = []

    def expand(self, texts: Sequence[str]) -> list[dict[str, float]]:
        self.calls.append(texts)
        return [{word: 1.0} for word in texts]


class RecordingValidator(GPUValidator):
    def __init__(self) -> None:
        super().__init__()
        self.called = False

    def validate(self) -> None:  # type: ignore[override]
        self.called = True


@dataclass
class Concept:
    label: str
    embedding_qwen: list[float] = field(default_factory=list)
    splade_terms: dict[str, float] = field(default_factory=dict)

    def to_embedding_text(self) -> str:
        return self.label


def test_embed_texts_updates_metrics() -> None:
    service = EmbeddingService(qwen=FakeQwen(), splade=FakeSplade())
    dense, sparse = service.embed_texts(["alpha", "beta"])
    assert len(dense) == 2
    assert len(sparse) == 2
    assert isinstance(service.metrics, EmbeddingMetrics)
    assert service.metrics.dense_tokens_per_second > 0
    assert service.metrics.sparse_terms_per_second >= 0


def test_embed_texts_invokes_gpu_validator() -> None:
    validator = RecordingValidator()
    service = EmbeddingService(qwen=FakeQwen(), splade=FakeSplade(), gpu_validator=validator)
    service.embed_texts(["alpha"])
    assert validator.called is True


def test_embed_concepts_assigns_vectors() -> None:
    service = EmbeddingService(qwen=FakeQwen(), splade=FakeSplade())
    concept = Concept("condition example")
    service.embed_concepts([concept])
    assert concept.embedding_qwen[0] == pytest.approx(len(concept.label))
    assert concept.splade_terms[concept.label] == 1.0
