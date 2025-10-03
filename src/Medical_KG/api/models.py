"""Pydantic request/response models for the public API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict

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


class VersionResponse(BaseModel):
    api_version: str
    component_versions: Dict[str, str]
    model_versions: Dict[str, str] = Field(default_factory=dict)


class KgNode(BaseModel):
    """Flexible KG node representation accepting arbitrary properties."""

    id: str
    label: str
    model_config = ConfigDict(extra="allow")


class KgRelationship(BaseModel):
    """Relationship between two KG nodes."""

    type: str
    start_id: str = Field(alias="start_id")
    end_id: str = Field(alias="end_id")
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class KgWriteRequest(BaseModel):
    nodes: List[KgNode] = Field(default_factory=list)
    relationships: List[KgRelationship] = Field(default_factory=list)
    graph: Dict[str, Any] | None = None


class KgWriteResponse(BaseModel):
    written_nodes: int
    written_relationships: int
