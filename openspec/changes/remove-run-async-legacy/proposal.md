# Proposal: Remove Legacy Pipeline Wrappers

## Why

After the successful `refactor-ingestion-pipeline-streaming` deployment, `IngestionPipeline.run_async_legacy()` remains as a compatibility shim. This method preserves the historic return signature, emits deprecation warnings, and increments dedicated telemetry counters. The migration window has closed with >95% adoption of the streaming API, but the legacy code path still exists in production, increasing maintenance burden and risking backsliding to deprecated patterns.

## What Changes

- **Delete deprecated wrapper**: Remove `IngestionPipeline.run_async_legacy()` and `_log_legacy_usage()` helper
- **Convert remaining callers**: Migrate any remaining internal code to `stream_events()` or `run_async()`
- **Remove consumption mode handling**: Drop `consumption_mode="run_async_legacy"` from events/emission logic
- **Purge environment toggles**: Delete `MEDICAL_KG_SUPPRESS_PIPELINE_DEPRECATION` and related env flag handling
- **Clean telemetry**: Remove legacy-specific metrics and dashboard panels
- **Update documentation**: Remove all references to legacy API from docs and runbooks

## Impact

**Affected specs**: `ingestion` (pipeline execution)

**Affected code**:

- `src/Medical_KG/ingestion/pipeline.py` - Delete deprecated methods (~80 lines)
- `src/Medical_KG/ingestion/events.py` - Remove legacy consumption mode tracking
- `tests/ingestion/test_pipeline.py` - Remove legacy test fixtures (~120 lines)
- `docs/ingestion_runbooks.md` - Remove legacy API documentation
- `ops/monitoring/grafana/` - Update dashboards to remove legacy panels

**Breaking Change**: YES - removes `run_async_legacy()` method (deprecated for 3+ months)

**Migration Path**: All callers should use `stream_events()` for streaming or `run_async()` for eager collection

**Benefits**:

- -200 lines of deprecated code removed
- Eliminates risk of new code using deprecated patterns
- Simplifies pipeline implementation and testing
- Removes telemetry overhead for unused metrics
- Clearer documentation focused on supported API
