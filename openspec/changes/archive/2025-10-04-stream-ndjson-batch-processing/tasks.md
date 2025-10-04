# Implementation Tasks

## 1. Refactor CLI Batch Loading

- [x] 1.1 Locate `_load_batch()` function in `src/Medical_KG/ingestion/cli.py`
- [x] 1.2 Change from `list(...)` to iterator pattern
- [x] 1.3 Remove eager materialization in `ingest()` command
- [x] 1.4 Test with small batch file (verify behavior unchanged)
- [x] 1.5 Test with large batch file (verify memory stays constant)

## 2. Add Pipeline Streaming Method

- [x] 2.1 Create `async def iter_results()` in `IngestionPipeline`
- [x] 2.2 Yield documents as adapters produce them
- [x] 2.3 Refactor `run_async()` to use `iter_results()` internally
- [x] 2.4 Maintain backward compatibility for `run_async()`
- [x] 2.5 Add type hints for async iterator protocol

## 3. Add Memory Tests

- [x] 3.1 Create memory profiling test helper (measure peak memory)
- [x] 3.2 Test CLI with 10K record batch (measure memory)
- [x] 3.3 Test CLI with 100K record batch (verify constant memory)
- [x] 3.4 Test pipeline streaming with large adapter results
- [x] 3.5 Add regression test to catch future memory leaks

## 4. Optional: Add Chunked Processing

- [x] 4.1 Add `--chunk-size` CLI flag (default: 1000)
- [x] 4.2 Process records in chunks for better batching
- [x] 4.3 Balance memory vs throughput (chunking reduces overhead)
- [x] 4.4 Document chunking behavior in CLI help text

## 5. Add Progress Reporting

- [x] 5.1 Add `rich` or `tqdm` dependency (optional)
- [x] 5.2 Show progress bar for batch processing
- [x] 5.3 Display: current record, total, ETA, records/sec
- [x] 5.4 Add `--quiet` flag to disable progress output
- [x] 5.5 Ensure progress works with streaming (incremental updates)

## 6. Update Tests

- [x] 6.1 Update existing batch tests to verify streaming behavior
- [x] 6.2 Add test for `iter_results()` method
- [x] 6.3 Test progress reporting (mock rich/tqdm)
- [x] 6.4 Test `--quiet` flag
- [x] 6.5 Verify no regressions in batch processing

## 7. Documentation

- [x] 7.1 Update ingestion runbooks with memory characteristics
- [x] 7.2 Document streaming vs batch trade-offs
- [x] 7.3 Add examples of large-scale batch processing
- [x] 7.4 Document chunking and progress reporting features
- [x] 7.5 Add troubleshooting for OOM scenarios

## 8. Validation

- [ ] 8.1 Run memory profiler on production-scale batch (1M records)
- [ ] 8.2 Verify constant memory usage (no growth)
- [ ] 8.3 Benchmark throughput (streaming vs old approach)
- [ ] 8.4 Test with real ingestion pipeline end-to-end
- [ ] 8.5 Verify all existing tests pass
