# Implementation Tasks

## 1. Design Event System

- [x] 1.1 Define `PipelineEvent` base class with common fields (timestamp, pipeline_id)
- [x] 1.2 Define `DocumentStarted` event (doc_id, adapter, parameters)
- [x] 1.3 Define `DocumentCompleted` event (document, duration, metadata)
- [x] 1.4 Define `DocumentFailed` event (doc_id, error, retry_count, is_retryable)
- [x] 1.5 Define `BatchProgress` event (completed_count, failed_count, remaining, eta)
- [x] 1.6 Define `AdapterStateChange` event (adapter, old_state, new_state, reason)
- [x] 1.7 Add comprehensive docstrings explaining when each event fires
- [x] 1.8 Create `PipelineResult` dataclass for backwards compatibility

## 2. Implement Streaming Core

- [x] 2.1 Create `src/Medical_KG/ingestion/events.py` module for event classes
- [x] 2.2 Add `IngestionPipeline.stream_events()` async iterator method
- [x] 2.3 Refactor adapter invocation to emit `DocumentStarted` before processing
- [x] 2.4 Emit `DocumentCompleted` after successful parse + validate
- [x] 2.5 Emit `DocumentFailed` on exceptions with retry context
- [x] 2.6 Emit `BatchProgress` every N documents (configurable, default 100)
- [x] 2.7 Emit `AdapterStateChange` for adapter lifecycle transitions
- [x] 2.8 Add comprehensive type hints for all event types

## 3. Update iter_results() for Backwards Compatibility

- [x] 3.1 Reimplement `iter_results()` as filter over `stream_events()`
- [x] 3.2 Extract `document` field from `DocumentCompleted` events
- [x] 3.3 Skip other event types silently
- [x] 3.4 Maintain identical behavior for existing callers
- [x] 3.5 Add deprecation notice (6-month migration to `stream_events()`)
- [x] 3.6 Update docstring to recommend `stream_events()` for new code

## 4. Create Convenience run_async() Wrapper

- [x] 4.1 Implement `run_async()` as eager consumer of `iter_results()`
- [x] 4.2 Collect all documents into list (document high memory usage)
- [x] 4.3 Collect all errors from `DocumentFailed` events
- [x] 4.4 Calculate aggregate statistics (success/fail counts, duration)
- [x] 4.5 Return `PipelineResult` with documents, errors, stats
- [x] 4.6 Add performance warning in docstring about memory usage
- [x] 4.7 Recommend `stream_events()` for large batches

## 5. Add Legacy Compatibility Layer

- [x] 5.1 Create `run_async_legacy()` with old signature
- [x] 5.2 Emit deprecation warning when called
- [x] 5.3 Delegate to new `run_async()` implementation
- [x] 5.4 Document 6-month deprecation timeline
- [x] 5.5 Add environment variable to silence warnings (for CI)
- [x] 5.6 Track usage metrics for migration monitoring

## 6. Update CLI to Use Streaming

- [ ] 6.1 Refactor `med ingest` command to consume `stream_events()`
- [ ] 6.2 Update progress bar to react to `BatchProgress` events
- [ ] 6.3 Display real-time counts from `DocumentCompleted` events
- [ ] 6.4 Show errors inline from `DocumentFailed` events
- [ ] 6.5 Add `--stream` flag to output NDJSON events to stdout
- [ ] 6.6 Add `--no-stream` flag to use legacy eager mode
- [ ] 6.7 Update help text with streaming examples

## 7. Add API Streaming Endpoint

- [ ] 7.1 Create `/api/ingestion/stream` POST endpoint
- [ ] 7.2 Accept adapter parameters as JSON body
- [ ] 7.3 Return Server-Sent Events (SSE) stream of pipeline events
- [ ] 7.4 Serialize events as JSON with event type discriminator
- [ ] 7.5 Handle client disconnection gracefully
- [ ] 7.6 Add rate limiting to prevent abuse
- [ ] 7.7 Document API with OpenAPI/Swagger examples

## 8. Implement Backpressure Mechanism

- [x] 8.1 Add configurable buffer size to `stream_events()` (default 100)
- [x] 8.2 Block adapter fetching when buffer is full
- [x] 8.3 Resume fetching when consumer drains buffer
- [x] 8.4 Add metrics for backpressure events (queue depth, wait time)
- [x] 8.5 Document backpressure behavior in pipeline guide
- [x] 8.6 Test with slow consumers (e.g., rate-limited API)

## 9. Add Checkpointing Support

- [ ] 9.1 Add `checkpoint_interval` parameter (default: every 1000 documents)
- [ ] 9.2 Emit `BatchProgress` at checkpoint boundaries
- [ ] 9.3 Allow consumers to persist state at checkpoints
- [ ] 9.4 Support resuming from checkpoint (doc_id list)
- [ ] 9.5 Add checkpoint metadata (timestamp, completed IDs)
- [ ] 9.6 Document checkpointing patterns in runbook

## 10. Add Event Filtering and Transformation

- [x] 10.1 Add `event_filter` callback parameter to `stream_events()`
- [x] 10.2 Allow filtering by event type (e.g., errors only)
- [x] 10.3 Add `event_transformer` for custom event enrichment
- [x] 10.4 Provide built-in filters (errors_only, progress_only)
- [x] 10.5 Document filter composition patterns
- [x] 10.6 Add examples for common filtering scenarios

## 11. Update Adapter Base Classes

- [ ] 11.1 Add optional `emit_event` callback to `BaseAdapter`
- [ ] 11.2 Adapters can emit custom events during fetch/parse/validate
- [ ] 11.3 Update `HttpAdapter` to emit retry events
- [ ] 11.4 Add adapter lifecycle state tracking
- [ ] 11.5 Document adapter event emission guidelines
- [ ] 11.6 Update adapter template with event examples

## 12. Add Comprehensive Tests

- [x] 12.1 Test `stream_events()` with mock adapter
- [x] 12.2 Test all event types are emitted correctly
- [x] 12.3 Test event ordering (Started → Completed/Failed)
- [x] 12.4 Test backpressure with slow consumer
- [ ] 12.5 Test checkpoint boundaries and resume
- [x] 12.6 Test filtering and transformation
- [x] 12.7 Test backwards compatibility via `iter_results()`
- [x] 12.8 Test `run_async()` aggregation logic
- [x] 12.9 Test error handling and retry events
- [ ] 12.10 Test concurrent pipeline execution
- [ ] 12.11 Integration test with real adapters
- [ ] 12.12 Performance test: 100k documents with streaming vs eager

## 13. Update Documentation

- [ ] 13.1 Add "Streaming Architecture" section to `docs/ingestion_runbooks.md`
- [ ] 13.2 Document all pipeline event types with examples
- [ ] 13.3 Add streaming patterns guide (progress tracking, checkpointing)
- [ ] 13.4 Document backpressure behavior and tuning
- [ ] 13.5 Add migration guide from eager to streaming
- [ ] 13.6 Update API documentation with SSE streaming endpoint
- [ ] 13.7 Add performance comparison: streaming vs eager
- [ ] 13.8 Document memory usage expectations

## 14. Add Observability Hooks

- [ ] 14.1 Add Prometheus metrics for event counts by type
- [ ] 14.2 Track pipeline duration distribution
- [ ] 14.3 Monitor backpressure queue depth
- [ ] 14.4 Track checkpoint latency
- [ ] 14.5 Add structured logging for events
- [ ] 14.6 Document metrics in operations manual

## 15. Migration Support

- [ ] 15.1 Create migration script to scan codebase for `run_async()` usage
- [ ] 15.2 Provide automated refactoring suggestions
- [ ] 15.3 Add lint rule to warn on legacy API usage
- [ ] 15.4 Update all internal usages to streaming
- [ ] 15.5 Communicate migration timeline to users
- [ ] 15.6 Track adoption metrics (legacy vs streaming usage)

## 16. Validation and Rollout

- [ ] 16.1 Run full test suite - all tests pass
- [ ] 16.2 Run mypy --strict - no type errors
- [ ] 16.3 Performance testing with large batches (1M+ documents)
- [ ] 16.4 Memory profiling to verify O(1) usage
- [ ] 16.5 Load testing on streaming API endpoint
- [ ] 16.6 Deploy to staging with real workloads
- [ ] 16.7 Monitor for regressions (latency, throughput, errors)
- [ ] 16.8 Gradual rollout with feature flag
- [ ] 16.9 Production deployment after 2-week staging validation
- [ ] 16.10 Post-deployment monitoring and support
