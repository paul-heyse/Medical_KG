# Implementation Tasks

## 1. Fixture & Mock Infrastructure

- [ ] 1.1 Create shared factories for documents, chunks, and API responses
- [ ] 1.2 Provide async transport mocks and service doubles (ingestion, retrieval)
- [ ] 1.3 Publish utilities under `tests/common` with type annotations

## 2. Ingestion & Retrieval Tests

- [ ] 2.1 Add integration tests for clinical/literature/guideline adapters (mocking external APIs)
- [ ] 2.2 Cover retrieval service flows (auth, caching, fallbacks) with typed tests
- [ ] 2.3 Exercise security modules (license enforcement, retention policies) in test harness

## 3. GPU & Embeddings Coverage

- [ ] 3.1 Simulate GPU validator scenarios (success/failure, fallback paths)
- [ ] 3.2 Validate embeddings monitoring/alerting logic with typed tests

## 4. Coverage Tooling

- [ ] 4.1 Replace manual tracing with pytest coverage configuration (per-file thresholds, html/xml reports)
- [ ] 4.2 Integrate coverage enforcement into pre-commit/CI (non-100% but realistic targets)
- [ ] 4.3 Document how to run coverage locally and interpret reports

## 5. Verification

- [ ] 5.1 Run full pytest suite with new fixtures and ensure stability
- [ ] 5.2 Generate coverage report and confirm agreed thresholds met
- [ ] 5.3 Update documentation and CI badges once new process lands
