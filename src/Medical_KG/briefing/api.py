"""FastAPI router exposing briefing endpoints."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from .models import Topic
from .repository import BriefingRepository, InMemoryBriefingRepository
from .service import BriefingService


@dataclass
class _Dependencies:
    repository: BriefingRepository


def _get_dependencies() -> _Dependencies:
    # default to empty repository; callers should override via dependency override in tests
    return _Dependencies(repository=InMemoryBriefingRepository())


def _get_service(
    deps: Annotated[_Dependencies, Depends(_get_dependencies)]
) -> BriefingService:
    return BriefingService(deps.repository)


router = APIRouter(prefix="/briefing", tags=["briefing"])


@router.post("/dossier")
async def create_dossier(
    request: dict[str, Any],
    service: Annotated[BriefingService, Depends(_get_service)],
) -> dict[str, Any]:
    try:
        topic = _parse_topic(request)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    format = request.get("format")
    try:
        return service.dossier(topic, format=format)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/evidence-map")
async def create_evidence_map(
    request: dict[str, Any],
    service: Annotated[BriefingService, Depends(_get_service)],
) -> dict[str, Any]:
    try:
        topic = _parse_topic(request)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    try:
        return service.evidence_map(topic)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/interview-kit")
async def create_interview_kit(
    request: dict[str, Any],
    service: Annotated[BriefingService, Depends(_get_service)],
) -> dict[str, Any]:
    try:
        topic = _parse_topic(request)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    try:
        return service.interview_kit(topic)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/coverage")
async def create_coverage(
    request: dict[str, Any],
    service: Annotated[BriefingService, Depends(_get_service)],
) -> dict[str, Any]:
    try:
        topic = _parse_topic(request)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    try:
        return service.coverage(topic)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/qa")
async def real_time_qa(
    request: dict[str, Any],
    service: Annotated[BriefingService, Depends(_get_service)],
) -> dict[str, Any]:
    try:
        topic = _parse_topic(request)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    query = request.get("query")
    if not isinstance(query, str) or not query.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="query is required")
    try:
        result = service.qa(topic, query)
    except KeyError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return {
        "answer": result.answer,
        "intent": result.intent,
        "evidence": list(result.evidence),
        "conflicts": list(result.conflicts),
        "gaps": list(result.gaps),
    }


def _parse_topic(request: dict[str, Any]) -> Topic:
    topic = request.get("topic")
    if not isinstance(topic, dict):
        raise KeyError("topic is required")
    condition = topic.get("condition")
    intervention = topic.get("intervention")
    outcome = topic.get("outcome")
    if not all(isinstance(value, str) and value for value in (condition, intervention, outcome)):
        raise KeyError("topic requires condition/intervention/outcome")
    return Topic(condition=condition, intervention=intervention, outcome=outcome)


__all__ = ["router"]
