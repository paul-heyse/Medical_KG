# Streaming Pipeline Architecture

## MODIFIED Requirements

### Requirement: Ingestion Pipeline Execution

The ingestion pipeline SHALL provide a streaming-first execution model with structured events, replacing eager evaluation as the primary API.

#### Scenario: Streaming event emission

- **WHEN** a pipeline executes via `stream_events()`
- **THEN** it SHALL emit `PipelineEvent` instances as processing occurs
- **AND** SHALL emit events in order: `DocumentStarted` → `DocumentCompleted` OR `DocumentFailed`
- **AND** SHALL emit `BatchProgress` events at configurable intervals
- **AND** SHALL maintain O(1) memory usage regardless of batch size
- **AND** SHALL support backpressure via bounded buffer

#### Scenario: Backwards-compatible eager execution

- **WHEN** a pipeline executes via `run_async()`
- **THEN** it SHALL consume the event stream eagerly
- **AND** SHALL return `PipelineResult` with aggregated statistics
- **AND** SHALL document high memory usage in docstring
- **AND** SHALL recommend streaming for large batches

#### Scenario: Document-only streaming

- **WHEN** a consumer uses `iter_results()`
- **THEN** it SHALL filter `stream_events()` for `DocumentCompleted` events only
- **AND** SHALL yield `Document` instances
- **AND** SHALL maintain backwards compatibility with existing code

## ADDED Requirements

### Requirement: Structured Pipeline Events

The ingestion pipeline SHALL emit typed events representing processing lifecycle and progress.

#### Scenario: Document lifecycle events

- **WHEN** processing begins for a document
- **THEN** the pipeline SHALL emit `DocumentStarted` with doc_id and adapter info
- **WHEN** processing completes successfully
- **THEN** the pipeline SHALL emit `DocumentCompleted` with the document and metadata
- **WHEN** processing fails
- **THEN** the pipeline SHALL emit `DocumentFailed` with error details and retry context

#### Scenario: Progress tracking events

- **WHEN** the pipeline processes N documents (default N=100)
- **THEN** it SHALL emit `BatchProgress` with counts and ETA
- **AND** SHALL include completed, failed, and in-flight counts
- **AND** SHALL calculate estimated time remaining if batch size is known

#### Scenario: Adapter lifecycle events

- **WHEN** an adapter state changes (initialized, fetching, complete, failed)
- **THEN** the pipeline SHALL emit `AdapterStateChange` with state transition details
- **AND** SHALL include reason for state change if available

### Requirement: Backpressure Management

The pipeline SHALL implement backpressure to prevent unbounded memory growth when consumers process slower than producers.

#### Scenario: Bounded event buffer

- **WHEN** `stream_events()` is called with buffer_size parameter
- **THEN** the pipeline SHALL use a bounded queue of that size
- **WHEN** the queue is full
- **THEN** the pipeline SHALL block adapter fetching until space is available
- **AND** SHALL emit backpressure metrics for monitoring

#### Scenario: Slow consumer handling

- **WHEN** a consumer processes events slowly
- **THEN** the pipeline SHALL automatically slow adapter fetching
- **AND** SHALL NOT accumulate unbounded documents in memory
- **AND** memory usage SHALL remain bounded by buffer size

### Requirement: Checkpointing Support

The pipeline SHALL enable consumers to checkpoint progress at defined boundaries for resumability.

#### Scenario: Checkpoint boundaries

- **WHEN** `BatchProgress` events are emitted
- **THEN** consumers CAN persist checkpoint state
- **WHEN** resuming from checkpoint
- **THEN** consumers CAN provide completed doc_id list to skip
- **AND** pipeline SHALL filter already-processed documents

### Requirement: Event Filtering and Transformation

The pipeline SHALL allow consumers to filter and transform events declaratively.

#### Scenario: Filter by event type

- **WHEN** consumer provides event_filter callback
- **THEN** only matching events SHALL be yielded
- **AND** non-matching events SHALL be silently skipped

#### Scenario: Transform events

- **WHEN** consumer provides event_transformer callback
- **THEN** events SHALL be transformed before yielding
- **AND** transformer CAN enrich events with additional metadata
