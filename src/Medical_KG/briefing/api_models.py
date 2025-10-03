"""Pydantic models for briefing API payloads."""
from __future__ import annotations

from typing import Annotated, Any

from pydantic import BaseModel, Field


class TopicPayload(BaseModel):
    condition: str
    intervention: str
    outcome: str


class DossierRequest(BaseModel):
    topic: TopicPayload
    format: str | None = None


class TopicOnlyRequest(BaseModel):
    topic: TopicPayload


class CoverageRequest(TopicOnlyRequest):
    pass


class EvidenceMapRequest(TopicOnlyRequest):
    pass


class InterviewKitRequest(TopicOnlyRequest):
    pass


class QARequest(BaseModel):
    topic: TopicPayload
    query: Annotated[str, Field(min_length=1)]


class QAResponse(BaseModel):
    answer: str
    intent: str
    evidence: list[Any]
    conflicts: list[Any]
    gaps: list[Any]


__all__ = [
    "CoverageRequest",
    "DossierRequest",
    "EvidenceMapRequest",
    "InterviewKitRequest",
    "QARequest",
    "QAResponse",
    "TopicOnlyRequest",
    "TopicPayload",
]
