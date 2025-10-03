# Logging & Tracing Standards

Medical KG emits structured JSON logs and OpenTelemetry traces to simplify operations and incident response.

## Structured Logging

- **Format** – `python-json-logger` encodes log records as JSON with the following fields:
  - `timestamp`: ISO8601 timestamp in UTC.
  - `level`: Log level (`DEBUG`, `INFO`, `WARNING`, `ERROR`).
  - `name`: Logger name / component.
  - `message`: Human-readable message.
  - `request_id`: Correlates API requests (populated by middleware).
  - `trace_id` / `span_id`: Derived from the active OpenTelemetry span when tracing is enabled.
- **Sampling** – Controlled via `MEDKG_LOG_SAMPLE_RATE` (default `1.0`). Values `<1` probabilistically drop lower-value logs while keeping errors.
- **Enrichment** – Additional context (service version, deployment region) may be attached via `configure_logging(extra_fields=...)` before app start.
- **Destination** – Logs flow to stdout. Forwarders (Fluent Bit, CloudWatch) should treat the payload as JSON and index `trace_id` for search.

## Tracing

- **Provider** – `setup_tracing()` configures the OpenTelemetry SDK with a `ParentBased(TraceIdRatioBased)` sampler. The sample rate is set by `MEDKG_TRACE_SAMPLE_RATE` (default `0.1`).
- **Export** – If `OTEL_EXPORTER_OTLP_ENDPOINT` is set, traces export via OTLP/HTTP. Otherwise spans print to stdout (`ConsoleSpanExporter`) for debugging.
- **Instrumentation** – FastAPI and HTTPX auto-instrumentation capture API latency, dependency calls, and propagate context headers (`traceparent`).
- **Service name** – Controlled by `MEDKG_SERVICE_NAME` (defaults to `medical-kg-api`).

## Operational Guidance

1. **Set sample rates deliberately** – During incidents, bump `MEDKG_TRACE_SAMPLE_RATE` to `1.0` to capture every request.
2. **Correlate logs & traces** – Search logs by `trace_id` to recover the full request path, then inspect the corresponding trace in Grafana Tempo / Jaeger.
3. **Redaction** – Sensitive payloads must be removed prior to logging. Use structured fields (`extra={"event": "..."}`) rather than string concatenation for safe redaction.
4. **Dashboards** – Grafana panels `API Latency` and `Trace Volume` overlay trace counts with P95 latency to detect sampling gaps.

Refer to `ops/monitoring/prometheus-alerts.yaml` for alert thresholds that rely on these observability primitives.
