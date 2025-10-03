from __future__ import annotations

import asyncio
from typing import Any, Mapping, Sequence

from Medical_KG.entity_linking import (
    Candidate,
    CandidateGenerator,
    DecisionEngine,
    DenseClient,
    DictionaryClient,
    EntityLinkingService,
    LlmAdjudicator,
    LlmClient,
    Mention,
    NerPipeline,
    SparseClient,
)


class StubNER(NerPipeline):
    def __call__(self, text: str) -> Sequence[Mention]:
        return [Mention(text="NCT01234567", start=0, end=11, label="trial")]


class StubDictionary(DictionaryClient):
    def search(self, text: str, *, fuzzy: bool = False) -> Sequence[Candidate]:
        return [
            Candidate(
                identifier="NCT01234567",
                ontology="clinicaltrials",
                score=0.6,
                label="Trial",
                metadata={},
            )
        ]


class StubSparse(SparseClient):
    def search(self, text: str) -> Sequence[Candidate]:
        return []


class StubDense(DenseClient):
    def search(self, text: str, context: str) -> Sequence[Candidate]:
        return []


class StubLlm(LlmClient):
    async def complete(self, *, prompt: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            "chosen_id": payload["candidates"][0]["identifier"],
            "ontology": payload["candidates"][0]["ontology"],
            "score": 0.8,
            "evidence_span": {"start": 0, "end": 11, "quote": payload["mention"]},
            "alternates": [],
            "notes": "",
        }


def test_entity_linking_accepts_high_confidence() -> None:
    generator = CandidateGenerator(
        dictionary=StubDictionary(),
        sparse=StubSparse(),
        dense=StubDense(),
    )
    service = EntityLinkingService(
        ner=StubNER(),
        generator=generator,
        adjudicator=LlmAdjudicator(StubLlm()),
        decision=DecisionEngine(acceptance_threshold=0.7),
    )
    results = asyncio.run(service.link("NCT01234567 trial", "context"))
    assert results
    result = results[0]
    assert result.decision.accepted is True
    assert result.decision.candidate is not None
    assert result.identifiers, "Deterministic identifier should be detected"
