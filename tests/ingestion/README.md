# Ingestion Test Harness

This directory hosts unit and integration-style tests for the ingestion subsystem. Key utilities live in
`tests/ingestion/fixtures/__init__.py`:

- `load_json_fixture` / `load_text_fixture` expose the canned upstream payloads stored under `tests/fixtures/ingestion/`.
- `FakeLedger` captures state transitions without writing to disk, mirroring `IngestionLedger` behaviour.
- `FakeRegistry` wires adapters into CLI flows without touching the global registry.
- `build_mock_transport` returns an `httpx.MockTransport` so adapters can exercise retry and pagination logic without issuing
  real network requests.
- `sample_document_factory` builds deterministic `Document` objects for CLI and pipeline tests.

Adapters are exercised via bootstrap payloads and the mock transport; no test performs network I/O. When adding new cases, use
`FakeLedger` for ledger assertions and extend the fixtures module instead of re-implementing ad hoc doubles.
