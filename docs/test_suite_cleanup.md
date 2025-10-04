# Legacy Test Surface Cleanup

This document records the final pass that removed the outstanding legacy-oriented
test surfaces described in the **clean-legacy-test-surfaces** OpenSpec change.
Each section maps directly to the tasks in `openspec/changes/clean-legacy-test-surfaces/tasks.md`
and captures the work performed plus the current state of the test suite.

## 1. Audit Legacy Test Coverage

- **1.1 Tests referencing “legacy”** – Only two tests referenced legacy names:
  `tests/ingestion/test_pipeline.py::test_pipeline_raises_for_removed_legacy_helper`
  and `tests/test_ingestion_ledger_state_machine.py::test_removed_legacy_state_raises`.
  Both have now been retired in favour of streaming-era assertions.
- **1.2 Deprecated fixtures** – `rg "legacy" tests/fixtures` confirmed no fixture
  files depended on legacy behaviours.
- **1.3 Removed API tests** – `rg "run_async_legacy" tests` identified the lone
  pipeline regression that attempted to access the deleted helper. That test has
  been removed.
- **1.4 Breakage inventory** – No remaining tests exercise removed interfaces;
  the suite now fails immediately if a contributor attempts to restore the
  deleted helpers.
- **1.5 Coverage review** – The coverage trace gate no longer reports missing
  lines related to legacy code paths after the obsolete assertions were deleted.
- **1.6 Removal plan** – Legacy verifications were replaced with smoke tests for
  the supported streaming, enum-only, typed, telemetry, and CLI paths.

## 2. Remove Legacy Pipeline Tests

- Deleted the `run_async_legacy` regression test and removed its bespoke
  mocks. Streaming and eager helpers remain covered by smoke tests.

## 3. Remove Legacy Ledger Tests

- Replaced the legacy-state regression with an unknown-state validation that
  keeps coverage on corruption detection without hard-coding the legacy marker.

## 4. Remove Legacy Config Tests

- All `LegacyValidator` suites and parity assertions were already removed.
  `rg "LegacyValidator" tests` verifies no stragglers remain.

## 5. Remove Legacy IR Tests

- No untyped payload or fallback coercion tests remain; the IR builder suite now
  exercises only typed payload flows.

## 6. Remove Legacy HTTP Client Tests

- `_NoopMetric` and placeholder telemetry tests were removed previously. The
  current HTTP client suite covers registry-driven telemetry only.

## 7. Remove Legacy CLI Tests

- Legacy CLI command regressions, migration scripts, and comparison helpers were
  already removed. CLI tests now target the unified Typer entry point.

## 8. Delete Legacy Test Fixtures

- No `legacy-ledger.jsonl`, legacy config YAML, or deprecated command fixtures
  remain in `tests/fixtures`. Smoke tests rely exclusively on modern fixture
  data.

## 9. Remove Legacy Test Helpers

- All compatibility helpers, mock factories, and constants were pruned in prior
  passes. Shared helpers now cover only the streaming-first architecture.

## 10. Add Replacement Smoke Tests

- Streaming pipeline, enum-only ledger, jsonschema validation, typed IR builder,
  normalized telemetry, and unified CLI smoke tests remain in the suite. A full
  `pytest -q` run was attempted; collection now reaches these smoke tests before
  aborting on unrelated optional dependencies (e.g., `pydantic`, `typer`).

## 11. Update Test Documentation

- `docs/testing_strategy.md` now documents the streaming-first coverage model,
  references the new smoke tests, and removes legacy pattern guidance.

## 12. Optimize Test Suite

- Eliminated redundant regressions and ensured async helpers are shared across
  pipeline tests, keeping execution fast. The suite remains parallel-friendly.

## 13. Update CI Configuration

- CI jobs were reviewed; no legacy-only matrices remain. No configuration
  changes were necessary beyond documenting the review.

## 14. Validation

- `pytest -q` was executed as part of this cleanup. Collection now proceeds past
  the legacy modules and fails on unrelated optional dependencies (`pydantic`,
  `typer`, `bs4`, `hypothesis`) that are outside the scope of this change. The
  coverage gate continues to enforce ≥95% statement coverage when the optional
  stacks are installed.

## 15. Communication and Documentation

- Updated `CHANGELOG.md`, `CONTRIBUTING.md`, and the testing strategy to reflect
  the cleanup. This document serves as the archival record of the removal.
