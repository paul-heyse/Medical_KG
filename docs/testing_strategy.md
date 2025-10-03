# Testing Strategy

The automated test suite exercises Medical_KG through fast unit tests, focused
integration tests, and scenario-level validations that run entirely offline.
This document summarizes expectations for contributors adding or updating
checks.

## Test Suite Structure

- **Unit tests** cover individual modules in isolation (e.g., briefing
  synthesis utilities, ingestion CLI). They use fixtures and lightweight
  doubles to cover success and failure paths.
- **Integration tests** assemble multiple layers (e.g., ingestion adapters,
  retrieval service) using fake transports and repositories so that behavior is
  deterministic and does not depend on third-party services.
- **Property and regression tests** focus on edge cases—boundary calculations
  and conflict detection—to guard against subtle regressions.

## Running Tests Locally

```bash
# run the default pytest suite with the trace-based coverage hook enabled
pytest -q
```

The suite uses a `trace`-backed coverage gate (see `tests/conftest.py`). If you
need to explore code interactively, set `DISABLE_COVERAGE_TRACE=1` in the
environment before invoking pytest.

## Coverage Expectations

- Total statement coverage for `src/Medical_KG` must remain at or above 95%.
- The gate writes `coverage_missing.txt` if new lines are untested—review this
  file for failing builds and add tests for the reported locations.

## Fixtures and Helpers

- Sample payloads live under `tests/fixtures`. Create shared factories when
  multiple tests require the same structures.
- For async code, prefer `pytest` fixtures that provide fake transports rather
  than real network clients. The local `httpx` shim and FastAPI stubs are
  available for offline execution.
- When a test needs to bypass coverage enforcement (for example, to measure
  raw coverage via `coverage.py`), set the `DISABLE_COVERAGE_TRACE` environment
  variable to `1`.

## Secrets and Environment Variables

Tests must not depend on real credentials. Default values for all required
configuration live in `.env.test` and `.env.example`. If a module references a
new secret, document the fake fallback here and update the env templates.

## Maintenance Workflow

1. Add or update tests alongside code changes.
2. Run `pytest -q`; if coverage fails, inspect `coverage_missing.txt` and update
   tests until the gap disappears.
3. Record notable testing patterns or fixtures in this document to aid future
   contributors.
