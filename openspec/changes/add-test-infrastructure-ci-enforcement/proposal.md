## Why

Test infrastructure is fragmented and CI coverage enforcement is missing. Shared fixtures are ad-hoc, async test helpers don't exist, and there are no test service fakes for integration tests. CI doesn't enforce coverage thresholds, publish reports, or track regressions. Without these, test quality degrades over time and coverage gaps reappear silently.

## What Changes

- Centralize test fixtures in `tests/conftest.py`: provide factories for documents, chunks, facets, extractions, users, and API responses.
- Create async test helpers: `AsyncMockTransport`, `async_test_client`, `mock_async_iterator`.
- Implement fake service implementations for integration tests: `FakeNeo4jService`, `FakeOpenSearchService`, `FakeKafkaProducer`, `FakeLLMService`.
- Configure pytest coverage: set minimum coverage to 95%, enable per-file coverage budgets, fail CI on regressions.
- Integrate coverage reporting into CI: generate HTML/XML reports, upload as artifacts, display in PR comments.
- Add coverage badge and dashboard: integrate with shields.io or Codecov.
- Document test infrastructure: create `tests/README.md` with fixture usage, mocking patterns, and contribution guidelines.

## Impact

- Affected specs: `testing` (ADDED: Test Infrastructure & Documentation, Coverage Reporting & Enforcement)
- Affected code: `tests/conftest.py` (expand significantly), `tests/helpers.py` (new), `tests/fakes.py` (new), `.github/workflows/test.yml` (new or update), `pyproject.toml` (pytest config), `tests/README.md` (new)
- Risks: refactoring existing tests to use new fixtures may introduce temporary breakage; mitigation via incremental migration and thorough testing of test infrastructure itself.
