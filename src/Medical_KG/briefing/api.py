"""FastAPI router exposing briefing endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from .api_models import (
    CoverageRequest,
    DossierRequest,
    EvidenceMapRequest,
    InterviewKitRequest,
    QARequest,
    QAResponse,
)
from .models import Topic
from .repository import BriefingRepository, InMemoryBriefingRepository
from .service import BriefingService


@dataclass
class _Dependencies:
    repository: BriefingRepository


def _get_dependencies() -> _Dependencies:
    # default to empty repository; callers should override via dependency override in tests
    return _Dependencies(repository=InMemoryBriefingRepository())


def _get_service(deps: Annotated[_Dependencies, Depends(_get_dependencies)]) -> BriefingService:
    return BriefingService(deps.repository)


router = APIRouter(prefix="/briefing", tags=["briefing"])


@router.post("/dossier")
async def create_dossier(
    request: DossierRequest,
    service: Annotated[BriefingService, Depends(_get_service)],
) -> dict[str, object]:
    topic = Topic(
        condition=request.topic.condition,
        intervention=request.topic.intervention,
        outcome=request.topic.outcome,
    )
    try:
        return service.dossier(topic, format=request.format)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/evidence-map")
async def create_evidence_map(
    request: EvidenceMapRequest,
    service: Annotated[BriefingService, Depends(_get_service)],
) -> dict[str, object]:
    topic = Topic(
        condition=request.topic.condition,
        intervention=request.topic.intervention,
        outcome=request.topic.outcome,
    )
    try:
        return service.evidence_map(topic)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/interview-kit")
async def create_interview_kit(
    request: InterviewKitRequest,
    service: Annotated[BriefingService, Depends(_get_service)],
) -> dict[str, object]:
    topic = Topic(
        condition=request.topic.condition,
        intervention=request.topic.intervention,
        outcome=request.topic.outcome,
    )
    try:
        return service.interview_kit(topic)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/coverage")
async def create_coverage(
    request: CoverageRequest,
    service: Annotated[BriefingService, Depends(_get_service)],
) -> dict[str, object]:
    topic = Topic(
        condition=request.topic.condition,
        intervention=request.topic.intervention,
        outcome=request.topic.outcome,
    )
    try:
        return service.coverage(topic)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/qa")
async def real_time_qa(
    request: QARequest,
    service: Annotated[BriefingService, Depends(_get_service)],
) -> QAResponse:
    topic = Topic(
        condition=request.topic.condition,
        intervention=request.topic.intervention,
        outcome=request.topic.outcome,
    )
    try:
        result = service.qa(topic, request.query)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return QAResponse(
        answer=result.answer,
        intent=result.intent,
        evidence=list(result.evidence),
        conflicts=list(result.conflicts),
        gaps=list(result.gaps),
    )


__all__ = ["router"]
