## Why

The test suite still blocks on coverage instrumentation (manual tracing demands 100%), lacks shared fixtures, and misses integration tests for ingestion/retrieval/security modules. Remaining TODOs in `add-test-coverage` prevent reliable CI.

## What Changes

- Build typed fixtures/mocks and avoid manual coverage tracing requirements
- Add targeted integration tests for ingestion adapters, retrieval service, security enforcement, and GPUs
- Establish pragmatic coverage thresholds in CI with generated reports

## Impact

- Affected specs: `testing`
- Affected code: `tests/`, coverage tooling, CI workflows
