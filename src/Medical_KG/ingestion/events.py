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
    """Base event emitted during pipeline execution.

    Every concrete event produced by :class:`IngestionPipeline` extends this
    dataclass to ensure consistent typing and serialisation semantics.
    """

    timestamp: float
    pipeline_id: str


@dataclass(slots=True)
class DocumentStarted(PipelineEvent):
    """Indicates that adapter processing for a document has begun.

    The pipeline emits this event immediately before handing a document off to
    downstream consumers, ensuring lifecycle events are observable even when
    the consumer processes slowly or fails mid-stream.
    """

    doc_id: str
    adapter: str
    parameters: Mapping[str, Any]


@dataclass(slots=True)
class DocumentCompleted(PipelineEvent):
    """Represents a successfully processed document.

    The attached :class:`~Medical_KG.ingestion.models.Document` contains the
    final parsed payload, while ``adapter_metadata`` carries any adapter
    specific information (HTTP timings, pagination cursors, etc.).
    """

    document: Document
    duration: float
    adapter_metadata: Mapping[str, Any]


@dataclass(slots=True)
class DocumentFailed(PipelineEvent):
    """Represents a document processing failure.

    The failure event preserves retry context so orchestrators can decide
    whether to requeue the document or surface the error to operators.
    """

    doc_id: str | None
    error: str
    retry_count: int
    is_retryable: bool
    error_type: str
    traceback: str | None = None


@dataclass(slots=True)
class BatchProgress(PipelineEvent):
    """Progress update emitted periodically during processing.

    Progress events expose throughput metrics, remaining counts (when known),
    and backpressure measurements derived from the bounded event queue.
    """

    completed_count: int
    failed_count: int
    in_flight_count: int
    queue_depth: int
    buffer_size: int
    remaining: int | None
    eta_seconds: float | None
    backpressure_wait_seconds: float
    backpressure_wait_count: int
    checkpoint_doc_ids: list[str] = field(default_factory=list)
    is_checkpoint: bool = False


@dataclass(slots=True)
class AdapterRetry(PipelineEvent):
    """Emitted when an HTTP adapter issues a retry for an upstream request."""

    adapter: str
    attempt: int
    error: str
    status_code: int | None


@dataclass(slots=True)
class AdapterStateChange(PipelineEvent):
    """Signals that an adapter has transitioned between lifecycle states.

    These events allow consumers to monitor adapter lifecycle, including
    transitions to failure states with accompanying reasons.
    """

    adapter: str
    old_state: str
    new_state: str
    reason: str | None


@dataclass(slots=True)
class PipelineResult:
    """Aggregated summary of a pipeline execution.

    Instances of this dataclass are returned by the eager convenience wrapper
    :meth:`IngestionPipeline.run_async` for compatibility with legacy code.
    """

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
    "AdapterRetry",
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
