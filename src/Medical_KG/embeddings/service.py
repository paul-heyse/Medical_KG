"""High-level embedding orchestration for dense and sparse representations."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import List, Sequence

from .gpu import GPURequirementError, GPUValidator
from .metrics import EMBEDDING_ERRORS, EMBEDDING_LATENCY, EMBEDDING_REQUESTS
from .qwen import QwenEmbeddingClient
from .splade import SPLADEExpander


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class EmbeddingMetrics:
    """Capture simple throughput metrics for embedding operations."""

    dense_tokens_per_second: float = 0.0
    dense_batch_size: int = 0
    sparse_terms_per_second: float = 0.0


@dataclass(slots=True)
class EmbeddingService:
    """Combine dense (Qwen) and sparse (SPLADE) embedding backends."""

    qwen: QwenEmbeddingClient
    splade: SPLADEExpander
    metrics: EmbeddingMetrics = field(default_factory=EmbeddingMetrics)
    gpu_validator: GPUValidator | None = None

    def embed_texts(
        self, texts: Sequence[str], *, sparse_texts: Sequence[str] | None = None
    ) -> tuple[List[List[float]], List[dict[str, float]]]:
        if not texts:
            return [], []
        device_label = "gpu" if self.gpu_validator else "cpu"
        if self.gpu_validator:
            try:
                self.gpu_validator.validate()
            except GPURequirementError:
                LOGGER.warning("GPU unavailable for embeddings, falling back to CPU")
                device_label = "cpu_fallback"
        dense_start = time.perf_counter()
        try:
            dense_vectors = self.qwen.embed(texts)
        except Exception:
            EMBEDDING_ERRORS.labels(model=self.qwen.model, device=device_label).inc()
            raise
        dense_duration = max(time.perf_counter() - dense_start, 1e-6)
        total_tokens = sum(len(text.split()) for text in texts)
        self.metrics.dense_tokens_per_second = total_tokens / dense_duration
        self.metrics.dense_batch_size = max(len(texts), 1)

        sparse_inputs = list(sparse_texts) if sparse_texts is not None else list(texts)
        sparse_start = time.perf_counter()
        sparse_vectors = self.splade.expand(sparse_inputs)
        sparse_duration = max(time.perf_counter() - sparse_start, 1e-6)
        total_terms = sum(len(terms) for terms in sparse_vectors)
        self.metrics.sparse_terms_per_second = total_terms / sparse_duration if total_terms else 0.0

        duration = max(time.perf_counter() - dense_start, 1e-6)
        EMBEDDING_REQUESTS.labels(model=self.qwen.model, device=device_label).inc(len(texts))
        EMBEDDING_LATENCY.labels(model=self.qwen.model, device=device_label).observe(duration)

        return dense_vectors, sparse_vectors

    def embed_concepts(self, concepts: Sequence["ConceptLike"]) -> None:
        texts = [concept.to_embedding_text() for concept in concepts]
        dense_vectors, sparse_vectors = self.embed_texts(texts)
        for concept, dense, sparse in zip(concepts, dense_vectors, sparse_vectors):
            concept.embedding_qwen = dense
            concept.splade_terms = sparse


class ConceptLike:
    """Protocol-like runtime type used for duck typing in embedding service."""

    embedding_qwen: List[float]
    splade_terms: dict[str, float]

    def to_embedding_text(self) -> str:  # pragma: no cover - documented contract
        raise NotImplementedError


__all__ = ["EmbeddingMetrics", "EmbeddingService"]
