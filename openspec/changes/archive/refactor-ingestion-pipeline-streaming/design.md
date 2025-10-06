# Streaming-First Pipeline Design

## Context

The current `IngestionPipeline` was designed around eager evaluation: `run_async()` fetches all documents, processes them, and returns a complete list. This works for small batches (< 10k documents) but fails for:

- Million-document catalog refreshes (OOM)
- Long-running auto-mode ingestion (unbounded memory)
- Real-time progress reporting (no events until complete)
- Distributed processing (no checkpointing)

`iter_results()` already exists as a streaming alternative but is treated as secondary, lacks structured events, and provides no progress/error visibility until iteration completes.

## Goals

- **Primary**: Make streaming the default execution model with O(1) memory usage
- **Observable**: Structured events for progress, errors, and lifecycle
- **Composable**: Easy to add checkpointing, fan-out, rate limiting
- **Compatible**: Backwards-compatible wrapper for eager evaluation
- **Performant**: No throughput regression vs current implementation

## Non-Goals

- **Not changing adapter interface**: Adapters continue to return `AsyncIterator[Any]`
- **Not changing Document model**: Document structure unchanged
- **Not adding distributed execution**: Single-process streaming only
- **Not replacing ledger**: Event system complements, doesn't replace ledger

## Decisions

### Decision 1: Event-Driven Architecture

**Choice**: Introduce `PipelineEvent` hierarchy as structured messages

**Event Types**:

```python
@dataclass
class PipelineEvent:
    timestamp: float
    pipeline_id: str

@dataclass
class DocumentStarted(PipelineEvent):
    doc_id: str
    adapter: str
    parameters: dict[str, Any]

@dataclass
class DocumentCompleted(PipelineEvent):
    document: Document
    duration: float
    adapter_metadata: dict[str, Any]

@dataclass
class DocumentFailed(PipelineEvent):
    doc_id: str | None
    error: str
    error_type: str
    retry_count: int
    is_retryable: bool
    traceback: str | None

@dataclass
class BatchProgress(PipelineEvent):
    completed: int
    failed: int
    in_flight: int
    estimated_total: int | None
    eta_seconds: float | None

@dataclass
class AdapterStateChange(PipelineEvent):
    adapter: str
    old_state: str
    new_state: str
    reason: str | None
```

**Rationale**:

- Type-safe: mypy can verify event handling
- Extensible: New event types don't break existing consumers
- Self-documenting: Fields explain what happened
- Testable: Easy to mock and assert on events

**Alternatives considered**:

- **Dict events**: Harder to type-check, easy to misuse
- **Callbacks**: Less composable, harder to test
- **Message queue**: Over-engineered for single-process

### Decision 2: Stream as Primary, Eager as Wrapper

**Choice**: `stream_events()` is the primary API, `run_async()` wraps it

**API Hierarchy**:

```python
# Primary: streaming
async def stream_events() -> AsyncIterator[PipelineEvent]:
    """Emit events as they occur. O(1) memory."""
    ...

# Convenience: filter to documents
async def iter_results() -> AsyncIterator[Document]:
    """Stream successful documents only."""
    async for event in stream_events():
        if isinstance(event, DocumentCompleted):
            yield event.document

# Convenience: eager evaluation
async def run_async() -> PipelineResult:
    """Collect all results. O(n) memory."""
    documents = [doc async for doc in iter_results()]
    return PipelineResult(documents=documents, ...)
```

**Rationale**:

- Single source of truth: All data flows through event stream
- Opt-in memory usage: Eager mode is explicit about cost
- Backwards compatible: Old code continues to work
- Incremental migration: Can adopt streaming gradually

**Alternatives considered**:

- **Both as primitives**: More code duplication, harder to maintain
- **Eager only**: Doesn't solve memory issues
- **Force migration**: Too disruptive for users

### Decision 3: Backpressure via AsyncIterator

**Choice**: Use native Python async iteration with bounded buffer

**Mechanism**:

```python
async def stream_events(self, buffer_size: int = 100) -> AsyncIterator[PipelineEvent]:
    queue = asyncio.Queue(maxsize=buffer_size)

    async def producer():
        async for raw in adapter.fetch():
            # Queue full? Block here until consumer drains
            await queue.put(DocumentStarted(...))
            document = adapter.parse(raw)
            await queue.put(DocumentCompleted(...))

    task = asyncio.create_task(producer())
    while not task.done() or not queue.empty():
        yield await queue.get()
```

**Rationale**:

- Natural Python idiom: No custom backpressure protocol
- Tunable: Buffer size controls memory/throughput trade-off
- Automatic: Slow consumer inherently slows producer
- Observable: Queue depth becomes a metric

**Alternatives considered**:

- **Unbounded queue**: Defeats memory goals
- **Manual signaling**: Complex, error-prone
- **Third-party library**: Unnecessary dependency

### Decision 4: Checkpointing via BatchProgress Events

**Choice**: Emit `BatchProgress` at configurable intervals, consumers decide what to checkpoint

**Pattern**:

```python
async for event in pipeline.stream_events():
    if isinstance(event, BatchProgress):
        # Consumer decides what to persist
        checkpoint = {
            "completed_ids": completed_ids,
            "timestamp": event.timestamp,
            "counts": (event.completed, event.failed)
        }
        await save_checkpoint(checkpoint)
    elif isinstance(event, DocumentCompleted):
        completed_ids.append(event.document.doc_id)
```

**Rationale**:

- Flexible: Consumer chooses checkpoint frequency and storage
- Decoupled: Pipeline doesn't know about checkpoint format
- Resumable: Consumer can filter already-completed IDs on restart
- Observable: Progress events double as checkpoint triggers

**Alternatives considered**:

- **Built-in checkpointing**: Too opinionated, limits flexibility
- **No checkpointing**: Leaves pattern undocumented
- **Ledger-only**: Too coupled to ledger implementation

### Decision 5: Migration Strategy

**Choice**: 6-month deprecation period with three API tiers

**Timeline**:

1. **Month 0**: Release with new streaming API
   - `stream_events()` stable and documented
   - `iter_results()` wraps `stream_events()` (no behavior change)
   - `run_async()` wraps `iter_results()` (adds memory warning)
   - `run_async_legacy()` available for explicit old behavior

2. **Month 3**: Deprecation warnings
   - `run_async_legacy()` emits warning on first call
   - Documentation recommends streaming for new code
   - Migration guide published

3. **Month 6**: Remove legacy
   - `run_async_legacy()` deleted
   - `run_async()` stays as eager wrapper (documented)
   - `iter_results()` stays as filter wrapper (documented)

**Rationale**:

- Non-breaking: All existing code continues to work
- Gradual: Users have time to migrate
- Clear: Three tiers signal recommendation order
- Measurable: Can track adoption via telemetry

## Risks / Trade-offs

### Risk 1: Increased Complexity

**Risk**: Event-driven architecture adds conceptual overhead

**Mitigation**:

- Comprehensive documentation with examples
- CLI uses streaming by default (demonstrates patterns)
- Convenience wrappers hide complexity for simple cases
- Clear error messages guide users to correct patterns

**Trade-off accepted**: Complexity is necessary for memory efficiency

### Risk 2: Performance Regression

**Risk**: Event emission and buffering could slow throughput

**Mitigation**:

- Benchmark before/after with 100k document batches
- Buffer tuning parameter for performance-critical paths
- Events are lightweight dataclasses (minimal overhead)
- Eager mode available if streaming proves slower

**Measurement**:

- Target: <5% throughput regression
- Acceptable: <10% regression for streaming
- Eager mode should match baseline

### Risk 3: Incomplete Migration

**Risk**: Old code continues using eager mode, doesn't realize benefits

**Mitigation**:

- Memory warnings in `run_async()` docstring
- Linter rule suggests streaming for large batches
- CI metrics track streaming vs eager usage
- Internal code migrated as part of rollout

## Migration Plan

### Phase 1: Implementation (Weeks 1-3)

1. Implement event system and `stream_events()`
2. Refactor `iter_results()` and `run_async()`
3. Add comprehensive tests
4. Update CLI to use streaming

### Phase 2: Staging (Weeks 4-5)

1. Deploy to staging environment
2. Run real workloads with streaming
3. Monitor performance and memory usage
4. Collect feedback from early adopters

### Phase 3: Production (Week 6)

1. Gradual rollout with feature flag
2. Monitor for regressions
3. Publish migration guide
4. Internal code migration

### Phase 4: Deprecation (Months 3-6)

1. Deprecation warnings added
2. External communication to users
3. Support migration questions
4. Track adoption metrics

### Phase 5: Cleanup (Month 6+)

1. Remove legacy APIs
2. Simplify documentation
3. Archive migration guide
4. Celebrate memory savings

## Success Criteria

- [ ] `stream_events()` implemented and tested
- [ ] Memory usage O(1) for arbitrarily large batches
- [ ] <10% throughput regression vs baseline
- [ ] All events documented with examples
- [ ] CLI uses streaming with progress bars
- [ ] Backwards compatibility maintained
- [ ] Migration guide published
- [ ] 80%+ internal adoption after 6 months

## Open Questions

1. **Should we add event replay for debugging?**
   - Proposal: Log events to file for post-mortem analysis
   - Decision: Add in follow-up if needed

2. **Should adapters emit custom events?**
   - Proposal: Allow adapters to emit domain-specific events
   - Decision: Yes, but document patterns carefully

3. **How to handle event serialization for API?**
   - Proposal: JSON with type discriminator (`{"type": "DocumentCompleted", ...}`)
   - Decision: Implement in API layer, not core pipeline

4. **Should we version events for backwards compatibility?**
   - Proposal: Add `version` field to `PipelineEvent`
   - Decision: Start with v1, add versioning if breaking changes needed
