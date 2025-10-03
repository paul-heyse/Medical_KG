"""Simple rule-based facet routing implementation."""
from __future__ import annotations

import re
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence

from Medical_KG.facets.models import FacetType

SECTION_TO_FACET: dict[str, FacetType] = {
    "indications": FacetType.PICO,
    "usage": FacetType.DOSE,
    "dosage": FacetType.DOSE,
    "dosage and administration": FacetType.DOSE,
    "adverse_reactions": FacetType.ADVERSE_EVENT,
    "safety": FacetType.ADVERSE_EVENT,
    "outcomes": FacetType.ENDPOINT,
    "results": FacetType.ENDPOINT,
    "eligibility": FacetType.ELIGIBILITY,
}

ENDPOINT_TERMS = re.compile(r"\b(HR|RR|OR|CI|hazard ratio|risk ratio|odds ratio)\b", re.I)
AE_TERMS = re.compile(r"\b(grade\s*[1-5]|adverse event|toxicity|serious)\b", re.I)
DOSE_TERMS = re.compile(r"\b(mg|mcg|tablet|capsule|po|iv|b.i.d|bid|q\d+h)\b", re.I)
PICO_TERMS = re.compile(r"\b(population|intervention|comparator|outcome|randomized|trial|patients?)\b", re.I)


class FacetRouter:
    """Detects likely facet types for a chunk of text."""

    def __init__(self, table_headers: Sequence[str] | None = None) -> None:
        self._table_headers = [header.lower() for header in (table_headers or [])]

    def _header_votes(self) -> Counter[FacetType]:
        votes: Counter[FacetType] = Counter()
        for header in self._table_headers:
            if any(term in header for term in ["outcome", "hazard", "risk", "ratio"]):
                votes[FacetType.ENDPOINT] += 2
            if any(term in header for term in ["ae", "adverse", "grade", "toxicity"]):
                votes[FacetType.ADVERSE_EVENT] += 2
        return votes

    @staticmethod
    def _text_votes(text: str) -> Counter[FacetType]:
        votes: Counter[FacetType] = Counter()
        if ENDPOINT_TERMS.search(text):
            votes[FacetType.ENDPOINT] += 1
        if AE_TERMS.search(text):
            votes[FacetType.ADVERSE_EVENT] += 1
        if DOSE_TERMS.search(text):
            votes[FacetType.DOSE] += 1
        if PICO_TERMS.search(text):
            votes[FacetType.PICO] += 1
        return votes

    @staticmethod
    def _section_votes(section: str | None) -> Counter[FacetType]:
        votes: Counter[FacetType] = Counter()
        if not section:
            return votes
        lowered = section.lower()
        for key, facet in SECTION_TO_FACET.items():
            if key in lowered:
                votes[facet] += 2
        return votes

    def detect(self, text: str, *, section: str | None = None) -> list[FacetType]:
        votes: Counter[FacetType] = Counter()
        votes.update(self._header_votes())
        votes.update(self._text_votes(text))
        votes.update(self._section_votes(section))
        if not votes:
            return [FacetType.GENERAL]
        ranked = sorted(votes.items(), key=lambda item: (-item[1], item[0].value))
        return [facet for facet, score in ranked if score > 0]

    @classmethod
    def detect_multiple(
        cls, chunks: Iterable[tuple[str, Mapping[str, Sequence[str] | str | None]]]
    ) -> dict[int, list[FacetType]]:
        routing: dict[int, list[FacetType]] = {}
        for idx, (text, metadata) in enumerate(chunks):
            table_headers_value = metadata.get("table_headers")
            if isinstance(table_headers_value, Sequence) and not isinstance(table_headers_value, str):
                headers = list(table_headers_value)
            elif isinstance(table_headers_value, str):
                headers = [table_headers_value]
            else:
                headers = []
            router = cls(table_headers=headers)
            section_value = metadata.get("section")
            section = section_value if isinstance(section_value, str) else None
            routing[idx] = router.detect(text, section=section)
        return routing
