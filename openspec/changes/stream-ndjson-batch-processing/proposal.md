# Stream NDJSON Batch Processing

## Why

The current CLI implementation loads entire NDJSON batch files into memory before processing:

```python
# Current: Loads entire file into memory
batch = list(_load_batch(batch_file))
for record in batch:
    process(record)
```

This causes Out-Of-Memory (OOM) errors for large re-ingestion campaigns:

- **10K records**: ~100MB memory (manageable)
- **100K records**: ~1GB memory (problematic)
- **1M+ records**: OOM crash

Large-scale re-ingestion is a common operational scenario (schema migrations, data fixes, full rebuilds). The current implementation cannot handle these without splitting files manually.

Similarly, `IngestionPipeline.run_async()` materializes all adapter results before returning, preventing streaming telemetry and incremental processing.

## What Changes

### CLI Batch Streaming

- Replace `list(_load_batch(...))` with iterator: `for record in _load_batch(...):`
- Refactor `_load_batch()` to yield records one at a time
- Add chunked processing (optional): process in batches of 1000 records
- **BREAKING**: None (behavior unchanged, only memory usage improves)

### Pipeline Result Streaming

- Add `IngestionPipeline.iter_results()` async iterator method
- Yield `Document` objects as adapters produce them
- Update `run_async()` to use `iter_results()` internally
- Enable streaming telemetry (emit metrics per document, not per batch)
- **BREAKING**: None (existing `run_async()` still works)

### Memory Profiling

- Add tests verifying constant memory usage for large batches
- Benchmark memory usage before/after changes
- Document memory characteristics in runbooks

### CLI Progress Reporting

- Add progress bar for batch processing (using `rich` or `tqdm`)
- Show current record, total processed, ETA
- Enable `--quiet` flag to disable progress output

## Impact

- **Affected specs**: None (performance improvement)
- **Affected code**:
  - `src/Medical_KG/ingestion/cli.py` (~10 lines changed)
  - `src/Medical_KG/ingestion/pipeline.py` (+30 lines for `iter_results()`)
  - `tests/ingestion/test_cli.py` (+20 lines for memory tests)
  - `tests/ingestion/test_pipeline.py` (+25 lines for streaming tests)
  - `docs/ingestion_runbooks.md` (+15 lines for memory characteristics)
- **Benefits**:
  - **Scalability**: Handle millions of records without OOM
  - **Faster feedback**: Streaming progress, not batch-wait
  - **Lower latency**: Start processing immediately
  - **Better monitoring**: Per-document telemetry
- **Memory Impact**: Constant O(1) memory instead of O(n)
- **Risk**: Low - backward compatible, pure optimization
