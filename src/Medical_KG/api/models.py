"""Pydantic request/response models for the public API."""

from __future__ import annotations

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

from Medical_KG.extraction.models import ExtractionEnvelope
from Medical_KG.facets.models import FacetModel


class ErrorDetail(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Annotated[list[ErrorDetail], Field(default_factory=list)]
    retriable: bool = False
    reference: str | None = None


class FacetGenerationRequest(BaseModel):
    chunk_ids: list[str]


class FacetGenerationResponse(BaseModel):
    facets_by_chunk: dict[str, list[FacetModel]]
    metadata: Annotated[dict[str, dict[str, str]], Field(default_factory=dict)]


class ChunkResponse(BaseModel):
    chunk_id: str
    doc_id: str
    text: str
    section: str | None = None
    facets: Annotated[list[FacetModel], Field(default_factory=list)]


class RetrieveFilters(BaseModel):
    facet_type: str | None = None


class RetrieveRequest(BaseModel):
    query: str
    intent: str | None = None
    filters: RetrieveFilters | None = None
    topK: Annotated[int, Field(default=5, alias="topK")]

    model_config = {"populate_by_name": True}


class RetrieveResult(BaseModel):
    chunk_id: str
    score: float
    snippet: str
    facet_types: list[str]


class RetrieveResponse(BaseModel):
    results: list[RetrieveResult]
    query_meta: dict[str, Any]


class ExtractionRequest(BaseModel):
    chunk_ids: list[str]


class ExtractionResponse(BaseModel):
    envelope: ExtractionEnvelope


class HealthResponse(BaseModel):
    status: str
    services: dict[str, str]
    timestamp: datetime


class VersionResponse(BaseModel):
    api_version: str
    component_versions: dict[str, str]
    model_versions: Annotated[dict[str, str], Field(default_factory=dict)]


class KgNode(BaseModel):
    """Flexible KG node representation accepting arbitrary properties."""

    id: str
    label: str
    model_config = ConfigDict(extra="allow")


class KgRelationship(BaseModel):
    """Relationship between two KG nodes."""

    type: str
    start_id: Annotated[str, Field(alias="start_id")]
    end_id: Annotated[str, Field(alias="end_id")]
    model_config = ConfigDict(extra="allow", populate_by_name=True)


class KgWriteRequest(BaseModel):
    nodes: Annotated[list[KgNode], Field(default_factory=list)]
    relationships: Annotated[list[KgRelationship], Field(default_factory=list)]
    graph: dict[str, Any] | None = None


class KgWriteResponse(BaseModel):
    written_nodes: int
    written_relationships: int
