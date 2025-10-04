"""Structured event primitives for the ingestion pipeline."""

from __future__ import annotations

import dataclasses
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping, MutableMapping

from Medical_KG.ingestion.models import Document


@dataclass(slots=True)
class PipelineEvent:
    """Base event emitted during pipeline execution."""

    timestamp: float
    pipeline_id: str


@dataclass(slots=True)
class DocumentStarted(PipelineEvent):
    """Indicates that processing for a document has begun."""

    doc_id: str | None
    adapter: str
    parameters: Mapping[str, Any]


@dataclass(slots=True)
class DocumentCompleted(PipelineEvent):
    """Represents a successfully processed document."""

    document: Document
    duration: float
    adapter_metadata: Mapping[str, Any]


@dataclass(slots=True)
class DocumentFailed(PipelineEvent):
    """Represents a document processing failure."""

    doc_id: str | None
    error: str
    retry_count: int
    is_retryable: bool
    error_type: str
    traceback: str | None = None


@dataclass(slots=True)
class BatchProgress(PipelineEvent):
    """Progress update emitted periodically during processing."""

    completed_count: int
    failed_count: int
    remaining: int | None
    eta_seconds: float | None


@dataclass(slots=True)
class AdapterStateChange(PipelineEvent):
    """Signals that an adapter has transitioned between lifecycle states."""

    adapter: str
    old_state: str
    new_state: str
    reason: str | None


@dataclass(slots=True)
class PipelineResult:
    """Aggregated summary of a pipeline execution."""

    source: str
    documents: list[Document]
    errors: list[DocumentFailed]
    success_count: int
    failure_count: int
    started_at: datetime
    completed_at: datetime

    @property
    def duration_seconds(self) -> float:
        return max((self.completed_at - self.started_at).total_seconds(), 0.0)

    @property
    def doc_ids(self) -> list[str]:
        return [document.doc_id for document in self.documents]


def build_pipeline_id(source: str) -> str:
    """Create a unique pipeline identifier for an execution."""

    return f"{source}:{uuid.uuid4().hex}"


EventFilter = Callable[[PipelineEvent], bool]
EventTransformer = Callable[[PipelineEvent], PipelineEvent | None]


def errors_only(event: PipelineEvent) -> bool:
    """Filter that only passes failure events."""

    return isinstance(event, DocumentFailed)


def progress_only(event: PipelineEvent) -> bool:
    """Filter that only passes batch progress events."""

    return isinstance(event, BatchProgress)


def event_to_dict(event: PipelineEvent) -> MutableMapping[str, Any]:
    """Convert a pipeline event to a JSON serialisable mapping."""

    payload: MutableMapping[str, Any] = dataclasses.asdict(event)
    payload["type"] = type(event).__name__
    if isinstance(event, DocumentCompleted):
        payload["document"] = event.document.as_record()
    return payload


__all__ = [
    "AdapterStateChange",
    "BatchProgress",
    "DocumentCompleted",
    "DocumentFailed",
    "DocumentStarted",
    "EventFilter",
    "EventTransformer",
    "PipelineEvent",
    "PipelineResult",
    "build_pipeline_id",
    "errors_only",
    "event_to_dict",
    "progress_only",
]
