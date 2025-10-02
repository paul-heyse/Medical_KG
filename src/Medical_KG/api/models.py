"""Pydantic request/response models for the public API."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from Medical_KG.extraction.models import ExtractionEnvelope
from Medical_KG.facets.models import FacetModel


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: List[ErrorDetail] = Field(default_factory=list)
    retriable: bool = False
    reference: Optional[str] = None


class FacetGenerationRequest(BaseModel):
    chunk_ids: List[str]


class FacetGenerationResponse(BaseModel):
    facets_by_chunk: Dict[str, List[FacetModel]]
    metadata: Dict[str, Dict[str, str]] = Field(default_factory=dict)


class ChunkResponse(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    section: Optional[str] = None
    facets: List[FacetModel] = Field(default_factory=list)


class RetrieveFilters(BaseModel):
    facet_type: Optional[str] = None


class RetrieveRequest(BaseModel):
    query: str
    intent: Optional[str] = None
    filters: Optional[RetrieveFilters] = None
    topK: int = Field(default=5, alias="topK")

    model_config = {"populate_by_name": True}


class RetrieveResult(BaseModel):
    chunk_id: str
    score: float
    snippet: str
    facet_types: List[str]


class RetrieveResponse(BaseModel):
    results: List[RetrieveResult]
    query_meta: Dict[str, Any]


class ExtractionRequest(BaseModel):
    chunk_ids: List[str]


class ExtractionResponse(BaseModel):
    envelope: ExtractionEnvelope


class HealthResponse(BaseModel):
    status: str
    services: Dict[str, str]
    timestamp: datetime
