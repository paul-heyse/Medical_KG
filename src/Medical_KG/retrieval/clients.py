"""Client abstractions used by retrieval pipeline."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Iterable, Mapping, Protocol, Sequence

from .models import RetrievalResult, RetrieverScores


class OpenSearchClient(Protocol):  # pragma: no cover - interface definition
    def search(self, *, index: str, body: Mapping[str, Any], size: int) -> Sequence[Mapping[str, Any]]:
        ...


class VectorSearchClient(Protocol):  # pragma: no cover - interface definition
    def query(self, *, index: str, embedding: Sequence[float], top_k: int) -> Sequence[Mapping[str, Any]]:
        ...


class EmbeddingClient(Protocol):  # pragma: no cover - interface definition
    def embed(self, text: str) -> Sequence[float]:
        ...


class SpladeEncoder(Protocol):  # pragma: no cover - interface definition
    def expand(self, text: str) -> Mapping[str, float]:
        ...


class Reranker(Protocol):  # pragma: no cover - interface definition
    async def rerank(self, query: str, candidates: Sequence[RetrievalResult]) -> Sequence[RetrievalResult]:
        ...


@dataclass(slots=True)
class InMemorySearchHit:
    chunk_id: str
    doc_id: str
    text: str
    title_path: str | None = None
    section: str | None = None
    score: float = 0.0
    start: int | None = None
    end: int | None = None
    metadata: Mapping[str, Any] | None = None

    def to_result(self, *, source: str) -> RetrievalResult:
        scores = RetrieverScores(**{source: self.score})
        return RetrievalResult(
            chunk_id=self.chunk_id,
            doc_id=self.doc_id,
            text=self.text,
            title_path=self.title_path,
            section=self.section,
            score=self.score,
            scores=scores,
            start=self.start,
            end=self.end,
            metadata=self.metadata or {},
        )


class InMemorySearch(OpenSearchClient):
    """Simple in-memory search client used for unit tests."""

    def __init__(self, hits: Iterable[InMemorySearchHit]):
        self._hits = list(hits)

    def search(self, *, index: str, body: Mapping[str, Any], size: int) -> Sequence[Mapping[str, Any]]:
        _ = index, body
        return [asdict(hit) for hit in self._hits[:size]]


class InMemoryVector(VectorSearchClient):
    """Simple vector search stub used in tests."""

    def __init__(self, hits: Iterable[InMemorySearchHit]):
        self._hits = list(hits)

    def query(self, *, index: str, embedding: Sequence[float], top_k: int) -> Sequence[Mapping[str, Any]]:
        _ = index, embedding
        return [asdict(hit) for hit in self._hits[:top_k]]


class PassthroughEncoder(SpladeEncoder):
    def __init__(self, mapping: Mapping[str, Mapping[str, float]] | None = None) -> None:
        self._mapping = dict(mapping or {})

    def expand(self, text: str) -> Mapping[str, float]:
        return self._mapping.get(text, {})


class ConstantEmbeddingClient(EmbeddingClient):
    def __init__(self, vector: Sequence[float] | None = None) -> None:
        self._vector = list(vector or [0.1, 0.2, 0.3])

    def embed(self, text: str) -> Sequence[float]:
        _ = text
        return list(self._vector)


__all__ = [
    "OpenSearchClient",
    "VectorSearchClient",
    "EmbeddingClient",
    "SpladeEncoder",
    "Reranker",
    "InMemorySearchHit",
    "InMemorySearch",
    "InMemoryVector",
    "PassthroughEncoder",
    "ConstantEmbeddingClient",
]
