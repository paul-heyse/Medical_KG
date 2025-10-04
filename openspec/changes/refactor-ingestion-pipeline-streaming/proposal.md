# Refactor Ingestion Pipeline to Streaming-First Architecture

## Why

The current `IngestionPipeline.run_async()` eagerly materializes all document IDs in memory before returning, causing:

**Memory Issues**:

- Large adapter runs (10k+ documents) accumulate full result lists
- Batch processing jobs hit OOM on multi-million record datasets
- No backpressure mechanism for downstream consumers

**Inconsistent APIs**:

- `iter_results()` streams lazily but is marked as secondary
- `run_async()` is the primary API but forces eager evaluation
- Callers must choose between memory efficiency and convenience
- No standard way to report progress during streaming

**Limited Observability**:

- No structured events for start/complete/fail per document
- Progress tracking requires custom instrumentation
- Retry logic hidden inside adapters
- Hard to add metrics or checkpoints mid-stream

From `repo_optimization_opportunities.md`: "Large adapter runs accumulate all results in memory even though `iter_results` already streams documents lazily. Downstream orchestration code must therefore choose between eager lists or rolling its own streaming loop."

## What Changes

### Make Streaming the Primary API

- Promote `iter_results()` to primary execution model
- `run_async()` becomes convenience wrapper that consumes iterator
- All new code should use streaming by default
- Document memory trade-offs clearly

### Introduce Structured Pipeline Events

Create `PipelineEvent` dataclass hierarchy:

- `DocumentStarted`: Signals adapter beginning to process a document
- `DocumentCompleted`: Successful document with metadata
- `DocumentFailed`: Error with context and retry info
- `BatchProgress`: Periodic progress updates with counts
- `AdapterStateChange`: Adapter lifecycle events

### Update Pipeline Interface

```python
class IngestionPipeline:
    async def stream_events(self) -> AsyncIterator[PipelineEvent]:
        """Primary API: Stream structured events."""
        ...

    async def iter_results(self) -> AsyncIterator[Document]:
        """Convenience: Stream only successful documents."""
        async for event in self.stream_events():
            if isinstance(event, DocumentCompleted):
                yield event.document

    async def run_async(self) -> PipelineResult:
        """Convenience: Eager evaluation (higher memory usage)."""
        documents = [doc async for doc in self.iter_results()]
        return PipelineResult(documents=documents, ...)
```

### Wire Progress Through Events

- Progress bars consume `BatchProgress` events
- Telemetry hooks receive all events
- Retry logic emits `DocumentFailed` with retry count
- Checkpointing can snapshot at `BatchProgress` boundaries

### Backpressure Support

- Consumers control iteration pace
- Adapters don't fetch ahead unbounded
- Ledger writes can be batched at event boundaries
- Memory usage stays O(1) relative to batch size

## Impact

- **Affected specs**: ingestion (pipeline interface changes)
- **Affected code**:
  - `src/Medical_KG/ingestion/pipeline.py` (major refactor, ~200 lines changed)
  - `src/Medical_KG/ingestion/models.py` (add `PipelineEvent` classes, +80 lines)
  - `src/Medical_KG/ingestion/cli.py` (update to consume events, ~50 lines changed)
  - `src/Medical_KG/api/ingestion.py` (streaming API endpoint, +40 lines)
  - All adapter test files (update to new event model)
  - `docs/ingestion_runbooks.md` (add streaming patterns section)
- **Benefits**:
  - **Memory efficient**: O(1) memory usage for arbitrarily large batches
  - **Backpressure**: Consumers control throughput
  - **Observable**: Structured events enable rich monitoring
  - **Composable**: Easy to add checkpointing, fan-out, filtering
- **Breaking changes**: **YES** - `run_async()` return type changes
  - Mitigation: Deprecation period with both APIs
  - Old API available as `run_async_legacy()` for 6 months
- **Risk**: Medium - core pipeline changes require careful testing
