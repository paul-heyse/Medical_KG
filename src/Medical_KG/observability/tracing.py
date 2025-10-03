"""OpenTelemetry tracing utilities."""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import ParentBased, TraceIdRatioBased

try:  # pragma: no cover - optional dependency
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
except Exception:  # pragma: no cover - exporter optional
    OTLPSpanExporter = None

__all__ = ["setup_tracing"]

_logger = logging.getLogger(__name__)
_configured = False


def setup_tracing(app: FastAPI | None = None) -> None:
    """Initialise OpenTelemetry tracing and instrument FastAPI/HTTPX."""

    global _configured
    if _configured:
        if app is not None:
            FastAPIInstrumentor.instrument_app(app)
        return

    service_name = os.getenv("MEDKG_SERVICE_NAME", "medical-kg-api")
    sample_rate = float(os.getenv("MEDKG_TRACE_SAMPLE_RATE", "0.1"))
    sampler = ParentBased(TraceIdRatioBased(max(0.0, min(sample_rate, 1.0))))
    provider = TracerProvider(resource=Resource.create({"service.name": service_name}), sampler=sampler)
    exporter = _build_exporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    HTTPXClientInstrumentor().instrument()
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
    else:  # pragma: no cover - defensive fallback
        FastAPIInstrumentor().instrument()

    _configured = True


def _build_exporter():
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
    if endpoint:
        if OTLPSpanExporter is None:
            _logger.warning("OTLP endpoint configured but opentelemetry-exporter-otlp is not installed")
        else:
            options: dict[str, str] = {}
            if headers:
                options["headers"] = headers
            return OTLPSpanExporter(endpoint=endpoint, **options)
    return ConsoleSpanExporter()
