"""Entity linking orchestration service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from .candidates import CandidateGenerator
from .decision import DecisionEngine, LinkingDecision
from .detectors import DeterministicDetectors, IdentifierCandidate
from .llm import AdjudicationResult, LlmAdjudicator
from .ner import Mention, NerPipeline


@dataclass(slots=True)
class LinkingResult:
    mention: Mention
    decision: LinkingDecision
    identifiers: Sequence[IdentifierCandidate]


class KnowledgeGraphWriter:
    def write(self, result: LinkingResult) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class EntityLinkingService:
    def __init__(
        self,
        *,
        ner: NerPipeline,
        generator: CandidateGenerator,
        adjudicator: LlmAdjudicator,
        decision: DecisionEngine,
        kg_writer: KnowledgeGraphWriter | None = None,
    ) -> None:
        self._ner = ner
        self._generator = generator
        self._adjudicator = adjudicator
        self._decision = decision
        self._kg = kg_writer
        self._detectors = DeterministicDetectors()

    async def link(self, text: str, context: str) -> List[LinkingResult]:
        mentions = self._ner(text)
        results: List[LinkingResult] = []
        for mention in mentions:
            identifiers = self._detectors.detect(mention.text)
            candidates = self._generator.generate(mention, context)
            fallback_reason = None
            try:
                llm = await self._adjudicator.adjudicate(mention, candidates, context)
            except Exception:
                llm = AdjudicationResult(
                    chosen_id=None,
                    ontology=None,
                    score=0.0,
                    evidence_span={},
                    alternates=[],
                    notes="llm-error",
                )
                fallback_reason = "llm-error"
            decision = self._decision.decide(llm, candidates, identifiers)
            if not decision.accepted and candidates:
                decision = LinkingDecision(
                    True, candidates[0], reason=fallback_reason or "fallback"
                )
            result = LinkingResult(mention=mention, decision=decision, identifiers=identifiers)
            if decision.accepted and self._kg:
                self._kg.write(result)
            results.append(result)
        return results


__all__ = ["EntityLinkingService", "LinkingResult", "KnowledgeGraphWriter"]
