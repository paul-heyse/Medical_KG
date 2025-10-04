# Proposal: Normalize HTTP Client Telemetry

## Why

The HTTP client currently uses `_NoopMetric` placeholders and implicit Prometheus detection for telemetry. After implementing the `add-http-client-telemetry` proposal with structured event hooks, these remnants create confusion and duplicate registration logic. The recent implementation shows telemetry properly integrated via callback hooks, but legacy `_NoopMetric` classes and old Prometheus discovery code still exist. Normalizing to a single telemetry interface simplifies the codebase and makes metrics configuration explicit.

## What Changes

- **Remove _NoopMetric scaffolding**: Delete placeholder metric classes
- **Centralize telemetry registration**: Use `_TelemetryRegistry` exclusively
- **Explicit metrics configuration**: Replace implicit detection with config flags
- **Delete unused discovery logic**: Remove orphaned Prometheus auto-detection
- **Update adapter instrumentation**: Use shared telemetry registry patterns
- **Simplify HTTP client constructor**: Clean up telemetry parameter handling

## Impact

**Affected specs**: `ingestion` (HTTP client telemetry)

**Affected code**:

- `src/Medical_KG/ingestion/http_client.py` - Remove `_NoopMetric` (~30 lines)
- `src/Medical_KG/ingestion/telemetry.py` - Centralize registration logic
- `src/Medical_KG/ingestion/adapters/http.py` - Update telemetry usage
- `tests/ingestion/test_http_client.py` - Update telemetry tests
- `docs/ingestion_runbooks.md` - Document explicit metrics configuration

**Breaking Change**: MINOR - changes default behavior (metrics now require explicit enablement)

**Migration Path**: Set `enable_metrics=True` in `AsyncHttpClient` constructor to restore auto-enabled Prometheus metrics

**Benefits**:

- -50 lines of placeholder/discovery code removed
- Single telemetry interface eliminates confusion
- Explicit configuration is more predictable
- ≤2% overhead compared to current implementation
- Clearer documentation for telemetry setup
- Simplified adapter telemetry patterns
