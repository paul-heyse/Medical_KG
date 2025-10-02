"""Simplified retrieval service that uses facet metadata for filtering and scoring."""
from __future__ import annotations

from dataclasses import dataclass

from Medical_KG.facets.models import FacetIndexRecord


@dataclass(slots=True)
class RetrievalResult:
    chunk_id: str
    score: float
    facet_types: list[str]
    snippet: str


class RetrievalService:
    """Scores chunks using naive BM25-like heuristics for tests."""

    def __init__(self) -> None:
        self._records: dict[str, FacetIndexRecord] = {}
        self._snippets: dict[str, str] = {}

    def upsert(self, record: FacetIndexRecord, snippet: str) -> None:
        self._records[record.chunk_id] = record
        self._snippets[record.chunk_id] = snippet

    def search(
        self,
        query: str,
        *,
        facet_type: str | None = None,
        top_k: int = 5,
    ) -> list[RetrievalResult]:
        query_terms = {term.lower() for term in query.split()}
        results: list[RetrievalResult] = []
        for chunk_id, record in self._records.items():
            if facet_type and facet_type not in record.facet_types:
                continue
            text = self._snippets.get(chunk_id, "")
            tokens = text.lower().split()
            overlap = len(query_terms.intersection(tokens))
            facet_bonus = 0.0
            if facet_type and facet_type in record.facet_types:
                facet_bonus = 1.6
            score = overlap + facet_bonus
            if score == 0:
                continue
            results.append(
                RetrievalResult(
                    chunk_id=chunk_id,
                    score=score,
                    facet_types=record.facet_types,
                    snippet=text[:160],
                )
            )
        return sorted(results, key=lambda item: item.score, reverse=True)[:top_k]
