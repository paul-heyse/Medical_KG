"""Deterministic client for Qwen embedding service (test-friendly)."""
from __future__ import annotations

import hashlib
import math
import random
from dataclasses import dataclass
from typing import Callable, List, Sequence


@dataclass(slots=True)
class QwenEmbeddingClient:
    """Client producing deterministic Qwen-style embeddings for tests."""

    model: str = "Qwen3-Embedding-8B"
    dimension: int = 4096
    batch_size: int = 256
    transport: Callable[[Sequence[str]], List[List[float]]] | None = None

    def embed(self, texts: Sequence[str]) -> List[List[float]]:
        """Embed a batch of texts, splitting into model-sized batches."""

        outputs: List[List[float]] = []
        for start in range(0, len(texts), self.batch_size):
            chunk = texts[start : start + self.batch_size]
            outputs.extend(self._embed_chunk(chunk))
        return outputs

    def _embed_chunk(self, texts: Sequence[str]) -> List[List[float]]:
        if self.transport:
            return self.transport(texts)
        vectors = [self._deterministic_vector(text) for text in texts]
        return [self._normalise(vector) for vector in vectors]

    def _deterministic_vector(self, text: str) -> List[float]:
        seed = hashlib.sha256((self.model + text).encode("utf-8")).digest()
        rnd = random.Random(seed)
        return [rnd.uniform(-1.0, 1.0) for _ in range(self.dimension)]

    def _normalise(self, vector: Sequence[float]) -> List[float]:
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


__all__ = ["QwenEmbeddingClient"]
