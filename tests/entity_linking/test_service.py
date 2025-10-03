from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from Medical_KG.entity_linking.candidates import Candidate, CandidateGenerator, DenseClient, DictionaryClient, SparseClient
from Medical_KG.entity_linking.decision import DecisionEngine, LinkingDecision
from Medical_KG.entity_linking.llm import LlmAdjudicator, LlmClient
from Medical_KG.entity_linking.ner import Mention, NerPipeline
from Medical_KG.entity_linking.service import EntityLinkingService, KnowledgeGraphWriter


class _StubNER(NerPipeline):
    def __call__(self, text: str) -> Sequence[Mention]:
        return [Mention(text=text, start=0, end=len(text), label="disease")]


@dataclass
class _StubDictionary(DictionaryClient):
    def search(self, text: str, *, fuzzy: bool = False) -> Sequence[Candidate]:
        return [Candidate(identifier="rx1", ontology="rxnorm", score=0.6, label=text, metadata={})]


@dataclass
class _StubSparse(SparseClient):
    def search(self, text: str) -> Sequence[Candidate]:
        return []


@dataclass
class _StubDense(DenseClient):
    def search(self, text: str, context: str) -> Sequence[Candidate]:
        return []


class _RecordingKG(KnowledgeGraphWriter):
    def __init__(self) -> None:
        self.written: list[LinkingDecision] = []

    def write(self, result) -> None:  # pragma: no cover - interface defined in tests
        self.written.append(result.decision)


class _SuccessfulClient(LlmClient):
    def __init__(self) -> None:
        self.payload: Mapping[str, Any] | None = None

    async def complete(self, *, prompt: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        self.payload = payload
        return {
            "chosen_id": payload["candidates"][0]["identifier"],
            "ontology": payload["candidates"][0]["ontology"],
            "score": 0.8,
        }


class _FailingClient(LlmClient):
    async def complete(self, *, prompt: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        raise TimeoutError("LLM timeout")


def _service(client: LlmClient, kg: KnowledgeGraphWriter | None = None) -> EntityLinkingService:
    generator = CandidateGenerator(
        dictionary=_StubDictionary(),
        sparse=_StubSparse(),
        dense=_StubDense(),
    )
    return EntityLinkingService(
        ner=_StubNER(),
        generator=generator,
        adjudicator=LlmAdjudicator(client),
        decision=DecisionEngine(acceptance_threshold=0.7),
        kg_writer=kg,
    )


def test_entity_linking_service_accepts_llm_choice() -> None:
    kg = _RecordingKG()
    client = _SuccessfulClient()
    service = _service(client, kg=kg)

    results = asyncio.run(service.link("aspirin", "context"))

    assert results and results[0].decision.accepted is True
    assert kg.written and kg.written[0].accepted is True
    assert client.payload is not None and client.payload["context"] == "context"


def test_entity_linking_service_falls_back_on_llm_failure() -> None:
    service = _service(_FailingClient())

    results = asyncio.run(service.link("aspirin", "context"))

    assert results[0].decision.accepted is True
    assert results[0].decision.reason in {"llm-error", "fallback"}


def test_entity_linking_service_handles_empty_mentions() -> None:
    class _EmptyNER(NerPipeline):
        def __call__(self, text: str) -> Sequence[Mention]:
            return []

    generator = CandidateGenerator(
        dictionary=_StubDictionary(),
        sparse=_StubSparse(),
        dense=_StubDense(),
    )
    service = EntityLinkingService(
        ner=_EmptyNER(),
        generator=generator,
        adjudicator=LlmAdjudicator(_SuccessfulClient()),
        decision=DecisionEngine(),
    )

    assert asyncio.run(service.link("", "ctx")) == []

