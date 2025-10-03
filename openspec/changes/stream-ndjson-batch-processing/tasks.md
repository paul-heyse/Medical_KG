# Implementation Tasks

## 1. Refactor CLI Batch Loading

- [ ] 1.1 Locate `_load_batch()` function in `src/Medical_KG/ingestion/cli.py`
- [ ] 1.2 Change from `list(...)` to iterator pattern
- [ ] 1.3 Remove eager materialization in `ingest()` command
- [ ] 1.4 Test with small batch file (verify behavior unchanged)
- [ ] 1.5 Test with large batch file (verify memory stays constant)

## 2. Add Pipeline Streaming Method

- [ ] 2.1 Create `async def iter_results()` in `IngestionPipeline`
- [ ] 2.2 Yield documents as adapters produce them
- [ ] 2.3 Refactor `run_async()` to use `iter_results()` internally
- [ ] 2.4 Maintain backward compatibility for `run_async()`
- [ ] 2.5 Add type hints for async iterator protocol

## 3. Add Memory Tests

- [ ] 3.1 Create memory profiling test helper (measure peak memory)
- [ ] 3.2 Test CLI with 10K record batch (measure memory)
- [ ] 3.3 Test CLI with 100K record batch (verify constant memory)
- [ ] 3.4 Test pipeline streaming with large adapter results
- [ ] 3.5 Add regression test to catch future memory leaks

## 4. Optional: Add Chunked Processing

- [ ] 4.1 Add `--chunk-size` CLI flag (default: 1000)
- [ ] 4.2 Process records in chunks for better batching
- [ ] 4.3 Balance memory vs throughput (chunking reduces overhead)
- [ ] 4.4 Document chunking behavior in CLI help text

## 5. Add Progress Reporting

- [ ] 5.1 Add `rich` or `tqdm` dependency (optional)
- [ ] 5.2 Show progress bar for batch processing
- [ ] 5.3 Display: current record, total, ETA, records/sec
- [ ] 5.4 Add `--quiet` flag to disable progress output
- [ ] 5.5 Ensure progress works with streaming (incremental updates)

## 6. Update Tests

- [ ] 6.1 Update existing batch tests to verify streaming behavior
- [ ] 6.2 Add test for `iter_results()` method
- [ ] 6.3 Test progress reporting (mock rich/tqdm)
- [ ] 6.4 Test `--quiet` flag
- [ ] 6.5 Verify no regressions in batch processing

## 7. Documentation

- [ ] 7.1 Update ingestion runbooks with memory characteristics
- [ ] 7.2 Document streaming vs batch trade-offs
- [ ] 7.3 Add examples of large-scale batch processing
- [ ] 7.4 Document chunking and progress reporting features
- [ ] 7.5 Add troubleshooting for OOM scenarios

## 8. Validation

- [ ] 8.1 Run memory profiler on production-scale batch (1M records)
- [ ] 8.2 Verify constant memory usage (no growth)
- [ ] 8.3 Benchmark throughput (streaming vs old approach)
- [ ] 8.4 Test with real ingestion pipeline end-to-end
- [ ] 8.5 Verify all existing tests pass
