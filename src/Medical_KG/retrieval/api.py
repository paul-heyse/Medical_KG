"""FastAPI bindings for the retrieval service."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Mapping, Sequence

from fastapi import APIRouter

from pydantic import BaseModel, Field, field_validator

from .models import RetrievalRequest, RetrieverTiming
from .service import RetrievalService
from .types import JSONValue


def _coerce_json(value: object) -> JSONValue:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return {str(key): _coerce_json(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_coerce_json(item) for item in value]
    raise ValueError("filters must contain JSON-serializable values")


class RetrieveQuery(BaseModel):
    """Inbound request payload for the retrieval endpoint."""

    query: str = Field(..., min_length=1)
    filters: dict[str, Any] = Field(default_factory=dict)
    topK: int | None = Field(default=None, ge=1, le=200)
    from_: int = Field(default=0, alias="from", ge=0)
    intent: str | None = None
    rerank_enabled: bool | None = None
    explain: bool = False

    @field_validator("filters", mode="before")
    @classmethod
    def _normalize_filters(cls, value: object) -> dict[str, Any]:
        if value is None:
            return {}
        if isinstance(value, Mapping):
            normalized: dict[str, JSONValue] = {}
            for key, item in value.items():
                if item is None:
                    continue
                normalized[str(key)] = _coerce_json(item)
            return normalized
        raise ValueError("filters must be a mapping of string keys")

    def to_request(self) -> RetrievalRequest:
        filters: dict[str, JSONValue] = {
            key: _coerce_json(value) for key, value in self.filters.items()
        }
        return RetrievalRequest(
            query=self.query,
            filters=filters,
            top_k=self.topK or 20,
            from_=self.from_,
            intent=self.intent,
            rerank_enabled=self.rerank_enabled,
            explain=self.explain,
        )


class RetrievalScoreModel(BaseModel):
    bm25: float | None = None
    splade: float | None = None
    dense: float | None = None
    fused: float | None = None
    rerank: float | None = None


class RetrievalResultModel(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    title_path: str | None = None
    section: str | None = None
    score: float
    scores: RetrievalScoreModel
    start: int | None = None
    end: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class TimingModel(BaseModel):
    component: str
    duration_ms: float

    @classmethod
    def from_dataclass(cls, timing: RetrieverTiming) -> "TimingModel":
        payload = asdict(timing)
        return cls(**payload)


class RetrievalMetaModel(BaseModel):
    intent_detected: str
    expanded_terms: dict[str, float]
    latency_ms: float
    timings: list[TimingModel]
    feature_flags: dict[str, Any]


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
                scores=RetrievalScoreModel(**result.scores.as_dict()),
                start=result.start,
                end=result.end,
                metadata=dict(result.metadata),
            )
            for result in response.results
        ]
        feature_flags_value = response.metadata.get("feature_flags")
        feature_flags = (
            dict(feature_flags_value) if isinstance(feature_flags_value, Mapping) else {}
        )
        meta = RetrievalMetaModel(
            intent_detected=response.intent,
            expanded_terms=dict(response.expanded_terms),
            latency_ms=response.latency_ms,
            timings=[TimingModel.from_dataclass(timing) for timing in response.timings],
            feature_flags=feature_flags,
        )
        return RetrievalResponseModel(results=results, query_meta=meta)

    return router


__all__ = ["create_router"]
