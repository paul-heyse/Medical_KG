# Ingestion Test Fixtures

This directory contains focused tests for the ingestion subsystem. Key fixtures live in
`tests/ingestion/fixtures/` and load canonical samples from `tests/fixtures/ingestion/` so
adapters can run against realistic payloads without hitting external APIs.

Shared test doubles live in `tests/conftest.py`:
- `FakeLedger` mimics the append-only JSONL ledger in memory, enabling assertions on state
  transitions without touching disk.
- `FakeRegistry` offers a simple adapter registry so CLI tests can substitute projection
  adapters and capture invocation parameters.
- `httpx_mock_transport` patches the ingestion HTTP client to use `httpx.MockTransport`
  for deterministic HTTP interactions.

Use these utilities when adding new tests so that ingestion behaviours stay hermetic and
coverage remains comprehensive.

## Optional Field Coverage

Optional field scenarios live in `tests/ingestion/test_optional_fields.py`. Each adapter family
defines fixtures with "all optional fields present" and "all optional fields absent" variants
under `tests/ingestion/fixtures/`. The parametrized tests exercise both variants to confirm that
`Document.raw` omits `NotRequired` keys when upstream payloads drop them and that validation logic
never raises due to missing optional data. When adding a new adapter:

- extend the relevant fixture module with helper functions that include and exclude the optional
  keys,
- add an `OptionalFieldScenario` entry so both variants run automatically, and
- update `tests/ingestion/OPTIONAL_FIELDS_COVERAGE.md` to record whether each optional field is
  commonly present (>80% of records) or rarely present (<20%).
