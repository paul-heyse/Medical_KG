from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Mapping


from Medical_KG.entity_linking.candidates import Candidate
from Medical_KG.entity_linking.llm import AdjudicationResult, LlmAdjudicator, LlmClient
from Medical_KG.entity_linking.ner import Mention


@dataclass
class _RecordingClient(LlmClient):
    payload: Mapping[str, Any] | None = None

    async def complete(self, *, prompt: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        self.payload = payload
        return {
            "chosen_id": payload["candidates"][0]["identifier"],
            "ontology": payload["candidates"][0]["ontology"],
            "score": 0.85,
            "evidence_span": {"start": 0, "end": len(payload["mention"]), "quote": payload["mention"]},
            "alternates": payload["candidates"],
            "notes": "confidence",
        }


def test_llm_adjudicator_builds_prompt() -> None:
    client = _RecordingClient()
    adjudicator = LlmAdjudicator(client)
    mention = Mention(text="aspirin", start=0, end=7, label="drug")
    candidates = [Candidate(identifier="rx1", ontology="rxnorm", score=0.8, label="aspirin", metadata={})]

    result = asyncio.run(adjudicator.adjudicate(mention, candidates, context="ctx"))

    assert isinstance(result, AdjudicationResult)
    assert client.payload is not None
    assert client.payload["mention"] == "aspirin"
    assert result.chosen_id == "rx1"

