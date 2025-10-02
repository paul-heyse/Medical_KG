"""FastAPI router exposing the /retrieve endpoint."""
from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, validator

from .models import RetrievalRequest
from .service import RetrievalService


class RetrieveQuery(BaseModel):
    query: str = Field(..., min_length=1)
    filters: Mapping[str, Any] | None = None
    topK: int | None = Field(default=None, ge=1, le=200)
    from_: int = Field(default=0, alias="from", ge=0)
    intent: str | None = None
    rerank_enabled: bool | None = None
    explain: bool = False

    @validator("filters", pre=True, always=True)
    def _normalize_filters(cls, value: Mapping[str, Any] | None) -> Mapping[str, Any]:
        return value or {}

    def to_request(self) -> RetrievalRequest:
        return RetrievalRequest(
            query=self.query,
            filters=self.filters or {},
            top_k=self.topK or 20,
            from_=self.from_,
            intent=self.intent,
            rerank_enabled=self.rerank_enabled,
            explain=self.explain,
        )


class RetrievalResultModel(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    title_path: str | None = None
    section: str | None = None
    score: float
    scores: Mapping[str, float]
    start: int | None = None
    end: int | None = None
    metadata: Mapping[str, Any] = Field(default_factory=dict)


class RetrievalMetaModel(BaseModel):
    intent_detected: str
    expanded_terms: Mapping[str, float]
    latency_ms: float
    timings: list[Mapping[str, Any]]
    feature_flags: Mapping[str, Any]


class RetrievalResponseModel(BaseModel):
    results: list[RetrievalResultModel]
    query_meta: RetrievalMetaModel


def create_router(service: RetrievalService) -> APIRouter:
    router = APIRouter(tags=["retrieval"])

    @router.post("/retrieve", response_model=RetrievalResponseModel)
    async def retrieve(payload: RetrieveQuery) -> RetrievalResponseModel:
        response = await service.retrieve(payload.to_request())
        results = [
            RetrievalResultModel(
                chunk_id=result.chunk_id,
                doc_id=result.doc_id,
                text=result.text,
                title_path=result.title_path,
                section=result.section,
                score=result.score,
                scores=result.scores.as_dict(),
                start=result.start,
                end=result.end,
                metadata=result.metadata,
            )
            for result in response.results
        ]
        meta = RetrievalMetaModel(
            intent_detected=response.intent,
            expanded_terms=response.expanded_terms,
            latency_ms=response.latency_ms,
            timings=[asdict(timing) for timing in response.timings],
            feature_flags=response.metadata.get("feature_flags", {}),
        )
        return RetrievalResponseModel(results=results, query_meta=meta)

    return router


__all__ = ["create_router"]
