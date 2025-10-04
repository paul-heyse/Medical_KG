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

## Streaming-First Smoke Tests

Core ingestion behaviours are guarded by lightweight smoke tests that exercise
the streaming pipeline, enum-only ledger transitions, strict jsonschema
validation, typed IR builder flows, normalized telemetry, and the unified CLI.
Keep these tests fast and deterministic—they validate wiring rather than edge
cases.

## Fixture Generation Guide

- Build fixtures under `tests/fixtures/` using modern enum and TypedDict
  structures. Legacy JSONL and YAML inputs were removed and should not be
  reintroduced.
- Prefer factories that synthesise streaming-era payloads (e.g.,
  `IngestionLedger` audit records) instead of copying historical legacy blobs.
- Document new fixture families here so contributors avoid reviving deprecated
  formats.

## Test Suite Architecture Overview

- **Ingestion pipeline** – Validates streaming runs, eager fallbacks, ledger
  integration, and telemetry counters.
- **Ledger state machine** – Enforces enum transitions and corruption detection
  without referencing removed legacy markers.
- **IR builder** – Exercises typed payload construction and rejects untyped or
  placeholder inputs.
- **HTTP client** – Covers telemetry registry integration and metric emission
  without `_NoopMetric` placeholders.
- **CLI** – Targets the unified Typer command surface; delegate comparisons to
  legacy CLIs have been retired.

## CI Integration

GitHub Actions runs `mypy --strict`, configuration validators, and the full
pytest suite. No legacy-specific jobs or matrices remain—any future additions
should follow the streaming-first assumptions described above.

## Extraction & Entity Linking Patterns

- Reuse `tests/extraction/conftest.py` fixtures for canonical clinical snippets,
  evidence spans, and extraction envelopes when authoring new tests. The
  fixtures cover PICO, effect, adverse event, dose, and eligibility scenarios.
- Mock external dependencies—LLM clients, spaCy pipelines, and terminology
  services—using lightweight dataclasses so tests remain deterministic and
  offline. See `tests/entity_linking/` for examples that stub dictionary,
  sparse, and dense retrieval clients alongside NER pipelines.
- Prefer exercising real normalization and validation flows (e.g.,
  `normalise_extractions`, `ExtractionValidator.validate`) rather than mocking
  internals to maintain coverage on critical heuristics.
