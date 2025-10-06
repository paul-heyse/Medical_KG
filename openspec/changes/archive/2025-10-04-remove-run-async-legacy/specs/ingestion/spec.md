# Spec Delta: Ingestion Pipeline (remove-run-async-legacy)

## REMOVED Requirements

### Requirement: Legacy Pipeline Wrapper API

**Reason**: Migration window closed with >95% streaming API adoption

**Migration**: Use `IngestionPipeline.stream_events()` for streaming consumption or `IngestionPipeline.run_async()` for eager collection

The legacy `run_async_legacy()` method provided backwards compatibility during the streaming migration. All production workloads have migrated to the streaming API.

### Requirement: Legacy Consumption Mode Tracking

**Reason**: No longer needed after legacy wrapper removal

**Migration**: Remove `consumption_mode` parameter from event processing logic

Consumption mode tracking was used to differentiate between legacy and streaming execution paths for metrics and debugging.

### Requirement: Legacy Deprecation Warnings

**Reason**: Method no longer exists, warnings obsolete

**Migration**: N/A - warnings were only emitted by removed legacy method

The deprecation warning system for `run_async_legacy()` included environment variable toggles and structured logging.

## MODIFIED Requirements

### Requirement: Pipeline Execution API

The ingestion pipeline SHALL provide streaming and eager execution modes without legacy compatibility layers.

**Modifications**:

- Removed legacy wrapper method and consumption mode tracking
- Simplified execution paths to streaming-first architecture
- Eliminated deprecation warning infrastructure

#### Scenario: Execute pipeline with streaming API

- **GIVEN** an `IngestionPipeline` instance
- **WHEN** `stream_events()` is called with adapter name and parameters
- **THEN** events are yielded as an async iterator
- **AND** no legacy consumption mode is tracked
- **AND** no deprecation warnings are emitted

#### Scenario: Execute pipeline with eager collection

- **GIVEN** an `IngestionPipeline` instance
- **WHEN** `run_async()` is called with adapter name and parameters
- **THEN** results are collected and returned as `list[PipelineResult]`
- **AND** streaming infrastructure is used internally
- **AND** no legacy wrapper methods are invoked

#### Scenario: Legacy method invocation fails

- **GIVEN** code attempting to call `run_async_legacy()`
- **WHEN** the method is invoked
- **THEN** an `AttributeError` is raised
- **AND** the error message suggests using `stream_events()` or `run_async()`

### Requirement: Pipeline Telemetry

The ingestion pipeline SHALL emit structured metrics for monitoring without legacy-specific counters.

**Modifications**:

- Removed `consumption_mode` label from `PIPELINE_CONSUMPTION_COUNTER`
- Simplified metric collection to streaming and eager modes only

#### Scenario: Telemetry excludes legacy mode

- **GIVEN** pipeline execution monitoring
- **WHEN** metrics are collected
- **THEN** consumption mode counters only track "stream_events" and "run_async"
- **AND** no "run_async_legacy" labels exist
- **AND** dashboards do not display legacy mode panels
