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
# run the default pytest suite with coverage enforcement enabled
pytest
```

`pytest-cov` enforces coverage targets using the defaults configured in
`pyproject.toml`. The command above produces `coverage.xml` and an HTML report in
`htmlcov/` for local inspection.

## Coverage Expectations

- Total statement coverage for `src/Medical_KG` must remain at or above 95%.
- The HTML report (`htmlcov/index.html`) and terminal summary highlight missing
  lines—treat any uncovered paths as bugs and add tests accordingly.

## Fixtures and Helpers

- Sample payloads live under `tests/fixtures`. Shared typed factories and mocks
  are published under `tests/common` to standardize ingestion/retrieval
  scenarios.
- For async code, prefer the doubles in `tests/common.mocks` instead of real
  network clients so tests stay offline.

## Secrets and Environment Variables

Tests must not depend on real credentials. Default values for all required
configuration live in `.env.test` and `.env.example`. If a module references a
new secret, document the fake fallback here and update the env templates.

## Maintenance Workflow

1. Add or update tests alongside code changes.
2. Run `pytest`; if coverage fails, inspect the terminal summary or
   `htmlcov/index.html` to identify gaps, then expand tests until the target is
   met.
3. Record notable testing patterns or fixtures in this document to aid future
   contributors.
