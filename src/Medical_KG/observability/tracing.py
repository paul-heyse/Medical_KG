"""OpenTelemetry tracing utilities."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any, cast

from fastapi import FastAPI

from Medical_KG.utils.optional_dependencies import MissingDependencyError, optional_import

__all__ = ["setup_tracing"]

_logger = logging.getLogger(__name__)
_configured = False
_components: _TracingComponents | None = None


@dataclass(frozen=True)
class _TracingComponents:
    trace_api: Any
    FastAPIInstrumentor: type[Any]
    HTTPXClientInstrumentor: type[Any]
    Resource: type[Any]
    TracerProvider: type[Any]
    BatchSpanProcessor: type[Any]
    ConsoleSpanExporter: type[Any]
    ParentBased: type[Any]
    TraceIdRatioBased: type[Any]


def _load_tracing_components() -> _TracingComponents:
    trace_api = optional_import(
        "opentelemetry.trace",
        feature_name="observability",
        package_name="opentelemetry-sdk",
    )
    fastapi_module = optional_import(
        "opentelemetry.instrumentation.fastapi",
        feature_name="observability",
        package_name="opentelemetry-instrumentation-fastapi",
    )
    httpx_module = optional_import(
        "opentelemetry.instrumentation.httpx",
        feature_name="observability",
        package_name="opentelemetry-instrumentation-httpx",
    )
    resources_module = optional_import(
        "opentelemetry.sdk.resources",
        feature_name="observability",
        package_name="opentelemetry-sdk",
    )
    trace_module = optional_import(
        "opentelemetry.sdk.trace",
        feature_name="observability",
        package_name="opentelemetry-sdk",
    )
    export_module = optional_import(
        "opentelemetry.sdk.trace.export",
        feature_name="observability",
        package_name="opentelemetry-sdk",
    )
    sampling_module = optional_import(
        "opentelemetry.sdk.trace.sampling",
        feature_name="observability",
        package_name="opentelemetry-sdk",
    )

    return _TracingComponents(
        trace_api=trace_api,
        FastAPIInstrumentor=cast(type[Any], fastapi_module.FastAPIInstrumentor),
        HTTPXClientInstrumentor=cast(type[Any], httpx_module.HTTPXClientInstrumentor),
        Resource=cast(type[Any], resources_module.Resource),
        TracerProvider=cast(type[Any], trace_module.TracerProvider),
        BatchSpanProcessor=cast(type[Any], export_module.BatchSpanProcessor),
        ConsoleSpanExporter=cast(type[Any], export_module.ConsoleSpanExporter),
        ParentBased=cast(type[Any], sampling_module.ParentBased),
        TraceIdRatioBased=cast(type[Any], sampling_module.TraceIdRatioBased),
    )


def setup_tracing(app: FastAPI | None = None) -> None:
    """Initialise OpenTelemetry tracing and instrument FastAPI/HTTPX."""

    global _configured, _components
    if _configured:
        if app is not None and _components is not None:
            _components.FastAPIInstrumentor.instrument_app(app)
        return

    components = _load_tracing_components()

    service_name = os.getenv("MEDKG_SERVICE_NAME", "medical-kg-api")
    sample_rate = float(os.getenv("MEDKG_TRACE_SAMPLE_RATE", "0.1"))
    sampler = components.ParentBased(
        components.TraceIdRatioBased(max(0.0, min(sample_rate, 1.0)))
    )
    provider = components.TracerProvider(
        resource=components.Resource.create({"service.name": service_name}),
        sampler=sampler,
    )
    exporter = _build_exporter(components.ConsoleSpanExporter)
    provider.add_span_processor(components.BatchSpanProcessor(exporter))
    components.trace_api.set_tracer_provider(provider)

    components.HTTPXClientInstrumentor().instrument()
    if app is not None:
        components.FastAPIInstrumentor.instrument_app(app)
    else:  # pragma: no cover - defensive fallback
        components.FastAPIInstrumentor().instrument()

    _components = components
    _configured = True


def _build_exporter(
    console_exporter_cls: type[Any],
) -> Any:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    headers = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
    if endpoint:
        try:
            exporter_module = optional_import(
                "opentelemetry.exporter.otlp.proto.http.trace_exporter",
                feature_name="observability",
                package_name="opentelemetry-sdk",
            )
        except MissingDependencyError:
            _logger.warning(
                "OTLP endpoint configured but opentelemetry-exporter-otlp is not installed",
            )
        else:
            exporter_cls = getattr(exporter_module, "OTLPSpanExporter", None)
            if exporter_cls is not None:
                options: dict[str, str] = {}
                if headers:
                    options["headers"] = headers
                return exporter_cls(endpoint=endpoint, **options)
            _logger.warning(
                "OTLP endpoint configured but OTLPSpanExporter symbol is unavailable",
            )
    return console_exporter_cls()
