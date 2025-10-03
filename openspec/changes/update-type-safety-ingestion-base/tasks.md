# Implementation Tasks

## 1. Typed Ingestion Models
- [x] 1.1 Introduce `TypedDict` definitions for raw payloads returned by ClinicalTrials.gov, openFDA, DailyMed, RxNorm, PubMed/PMC/MedRxiv, and guideline adapters.
- [x] 1.2 Update `Document`/`IngestionResult` dataclasses to use precise `Mapping`/`MutableMapping` generics (no `Any`).

## 2. Adapter Pipelines
- [x] 2.1 Annotate `BaseAdapter.run` and sibling methods to return concrete iterator types (e.g., `AsyncIterator[ClinicalStudyPayload]`).
- [x] 2.2 Update each adapter’s `fetch/parse/validate` signature to consume and emit typed objects; ensure error handling preserves doc IDs as `str`.
- [x] 2.3 Add adapter-focused unit tests (or fixtures) verifying typed payloads surface expected fields and validation rejects malformed input.

## 3. HTTP Client & Registry
- [x] 3.1 Replace `AsyncHttpClient` return values with typed wrappers for JSON/text/bytes and expose typed rate limiter structures.
- [x] 3.2 Annotate ledger (`LedgerEntry`, `IngestionLedger.record/get/entries`) and registry factories so adapter lookup stays type-safe.
- [x] 3.3 Update ingestion CLI helpers to propagate typed arguments and return lists with concrete element types.

## 4. Tooling & Verification
- [ ] 4.1 Ensure any required type stubs (e.g., `types-jsonschema`) are installed or vendored.
- [ ] 4.2 Run `mypy --strict src/Medical_KG/ingestion` and add the path to CI enforcement.
- [x] 4.3 Execute targeted ingestion adapter tests (clinical, guideline, literature, terminology) to confirm behavior is unchanged.
