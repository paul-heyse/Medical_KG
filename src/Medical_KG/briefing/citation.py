"""Citation utilities ensuring coverage guarantees."""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable, Mapping, MutableMapping, Sequence

from .models import Citation


class CitationError(RuntimeError):
    """Raised when citations are missing or invalid."""


class CitationManager:
    """Validates and deduplicates citations across briefing artifacts."""

    def __init__(self, existing_documents: Mapping[str, int] | None = None) -> None:
        self._documents = dict(existing_documents or {})

    def validate(self, citations: Iterable[Sequence[Citation]]) -> None:
        for group in citations:
            if not group:
                raise CitationError("Assertion missing citation")
            for citation in group:
                if citation.start < 0 or citation.end <= citation.start:
                    raise CitationError(f"Invalid citation offsets for {citation.doc_id}")
                expected_length = self._documents.get(citation.doc_id)
                if expected_length is not None and citation.end > expected_length:
                    raise CitationError(f"Citation exceeds document bounds for {citation.doc_id}")

    def aggregate(self, citations: Iterable[Citation]) -> list[dict[str, object]]:
        grouped: MutableMapping[str, dict[str, object]] = {}
        for citation in citations:
            key = f"{citation.doc_id}:{citation.start}:{citation.end}"
            if key not in grouped:
                grouped[key] = dict(citation.as_dict())
        return list(grouped.values())

    def bibliography(self, citations: Iterable[Citation]) -> list[dict[str, object]]:
        counts: MutableMapping[str, int] = defaultdict(int)
        for citation in citations:
            counts[citation.doc_id] += 1
        return [
            {"doc_id": doc_id, "citation_count": count}
            for doc_id, count in sorted(counts.items(), key=lambda item: item[0])
        ]


__all__ = ["CitationManager", "CitationError"]
