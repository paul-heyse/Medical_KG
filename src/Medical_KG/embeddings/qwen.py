"""Deterministic client for Qwen embedding service (test-friendly)."""

from __future__ import annotations

import hashlib
import math
import random
import time
from dataclasses import dataclass
from typing import Callable, List, Sequence

from Medical_KG.compat import ClientProtocol, create_client


@dataclass(slots=True)
class QwenEmbeddingClient:
    """Client producing deterministic Qwen-style embeddings for tests."""

    model: str = "Qwen3-Embedding-8B"
    dimension: int = 4096
    batch_size: int = 256
    transport: Callable[[Sequence[str]], List[List[float]]] | None = None
    api_url: str | None = None
    timeout: float = 10.0
    max_retries: int = 3
    http_client_factory: Callable[[], ClientProtocol] | None = None
    sleep: Callable[[float], None] = time.sleep

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
        if self.api_url:
            return self._embed_via_http(texts)
        vectors = [self._deterministic_vector(text) for text in texts]
        return [self._normalise(vector) for vector in vectors]

    def _embed_via_http(self, texts: Sequence[str]) -> List[List[float]]:
        payload = {"model": self.model, "input": list(texts)}
        attempt = 0
        last_error: Exception | None = None
        while attempt < self.max_retries:
            attempt += 1
            try:
                client = (
                    self.http_client_factory()
                    if self.http_client_factory
                    else create_client(timeout=self.timeout)
                )
                try:
                    response = client.post(self.api_url, json=payload)
                    response.raise_for_status()
                    data = response.json()
                    vectors = [item["embedding"] for item in data.get("data", [])]
                    if len(vectors) != len(texts):
                        raise ValueError("embedding service returned unexpected vector count")
                    return vectors
                finally:
                    if self.http_client_factory is None:
                        client.close()
            except Exception as exc:  # pragma: no cover - exercised via retries in tests
                last_error = exc
                if attempt >= self.max_retries:
                    raise
                self.sleep(0.2 * attempt)
        if last_error:
            raise last_error
        return []

    def _deterministic_vector(self, text: str) -> List[float]:
        seed = hashlib.sha256((self.model + text).encode("utf-8")).digest()
        rnd = random.Random(seed)
        return [rnd.uniform(-1.0, 1.0) for _ in range(self.dimension)]

    def _normalise(self, vector: Sequence[float]) -> List[float]:
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


__all__ = ["QwenEmbeddingClient"]
