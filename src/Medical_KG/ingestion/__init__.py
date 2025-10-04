"""Ingestion subsystem for external data sources."""

from .http_client import AsyncHttpClient
from .ledger import IngestionLedger
from .models import Document, IngestionResult
from .pipeline import IngestionPipeline, PipelineResult
from .registry import available_sources, get_adapter
from .telemetry import (
    CompositeTelemetry,
    HttpBackoffEvent,
    HttpErrorEvent,
    HttpRequestEvent,
    HttpResponseEvent,
    HttpRetryEvent,
    LoggingTelemetry,
    PrometheusTelemetry,
    TracingTelemetry,
    generate_request_id,
)

__all__ = [
    "AsyncHttpClient",
    "IngestionLedger",
    "Document",
    "IngestionResult",
    "IngestionPipeline",
    "PipelineResult",
    "available_sources",
    "get_adapter",
    "CompositeTelemetry",
    "HttpBackoffEvent",
    "HttpErrorEvent",
    "HttpRequestEvent",
    "HttpResponseEvent",
    "HttpRetryEvent",
    "LoggingTelemetry",
    "PrometheusTelemetry",
    "TracingTelemetry",
    "generate_request_id",
]
