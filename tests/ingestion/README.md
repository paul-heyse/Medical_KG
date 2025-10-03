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
