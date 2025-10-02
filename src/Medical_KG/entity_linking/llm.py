"""LLM adjudication helper."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .candidates import Candidate
from .ner import Mention


class LlmClient:
    async def complete(self, *, prompt: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:  # pragma: no cover
        raise NotImplementedError


@dataclass(slots=True)
class AdjudicationResult:
    chosen_id: str | None
    ontology: str | None
    score: float
    evidence_span: Mapping[str, Any]
    alternates: Sequence[Mapping[str, Any]]
    notes: str | None


class LlmAdjudicator:
    def __init__(self, client: LlmClient) -> None:
        self._client = client

    async def adjudicate(self, mention: Mention, candidates: Sequence[Candidate], context: str) -> AdjudicationResult:
        payload = {
            "mention": mention.text,
            "context": context,
            "candidates": [
                {
                    "identifier": candidate.identifier,
                    "ontology": candidate.ontology,
                    "score": candidate.score,
                    "label": candidate.label,
                }
                for candidate in candidates
            ],
        }
        response = await self._client.complete(prompt="entity_linking", payload=payload)
        return AdjudicationResult(
            chosen_id=response.get("chosen_id"),
            ontology=response.get("ontology"),
            score=float(response.get("score", 0.0)),
            evidence_span=response.get("evidence_span", {}),
            alternates=response.get("alternates", []),
            notes=response.get("notes"),
        )


__all__ = ["LlmAdjudicator", "AdjudicationResult", "LlmClient"]
