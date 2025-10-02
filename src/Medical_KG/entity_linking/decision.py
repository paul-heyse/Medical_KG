"""Decision logic for entity linking outputs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from .candidates import Candidate
from .detectors import IdentifierCandidate
from .llm import AdjudicationResult


@dataclass(slots=True)
class LinkingDecision:
    accepted: bool
    candidate: Candidate | None
    reason: str | None = None


class DecisionEngine:
    def __init__(self, *, acceptance_threshold: float = 0.7) -> None:
        self._threshold = acceptance_threshold

    def decide(
        self,
        llm: AdjudicationResult,
        candidates: Sequence[Candidate],
        identifiers: Sequence[IdentifierCandidate],
    ) -> LinkingDecision:
        if llm.chosen_id:
            candidate_map = {candidate.identifier: candidate for candidate in candidates}
            chosen = candidate_map.get(llm.chosen_id)
            if chosen and llm.score >= self._threshold:
                return LinkingDecision(True, chosen)
        if identifiers:
            deterministic = max(identifiers, key=lambda item: item.confidence)
            chosen = Candidate(
                identifier=deterministic.code,
                ontology=deterministic.scheme,
                score=deterministic.confidence,
                label=deterministic.code,
                metadata={},
            )
            return LinkingDecision(True, chosen, reason="deterministic")
        return LinkingDecision(False, None, reason="low-confidence")


__all__ = ["DecisionEngine", "LinkingDecision"]
