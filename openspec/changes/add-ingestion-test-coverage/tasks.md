# Implementation Tasks

## 1. Test Fixtures & Mocks

- [ ] 1.1 Create `tests/ingestion/fixtures/` with sample API responses (ClinicalTrials.gov XML, PubMed JSON, PMC XML, medRxiv JSON, UMLS, RxNorm)
- [ ] 1.2 Implement `httpx.MockTransport` factory in `tests/conftest.py` for adapter tests
- [ ] 1.3 Add `FakeLedger` and `FakeRegistry` test doubles for integration-style tests
- [ ] 1.4 Provide `sample_document_factory` fixture for downstream tests

## 2. Clinical Trials Adapter Tests

- [ ] 2.1 Test successful study fetch and parsing (NCT ID, title, conditions, arms, outcomes, eligibility)
- [ ] 2.2 Test partial data scenarios (missing arms, no outcomes, incomplete eligibility)
- [ ] 2.3 Test API error responses (404, 500, rate limiting with `Retry-After`)
- [ ] 2.4 Test metadata enrichment (sponsor, phase, enrollment, dates)
- [ ] 2.5 Test pagination and batch fetching

## 3. Literature Adapter Tests

- [ ] 3.1 PubMed: test article fetch by PMID, metadata extraction, abstract parsing
- [ ] 3.2 PMC: test full-text XML fetch, section extraction, references parsing
- [ ] 3.3 medRxiv: test preprint fetch, author/affiliation extraction, version tracking
- [ ] 3.4 Test fallback chain (PMC → PubMed → medRxiv)
- [ ] 3.5 Test rate limiting and retry logic for NCBI E-utilities

## 4. Guidelines & Terminology Adapter Tests

- [ ] 4.1 GuidelinesAdapter: test guideline document fetch, structured parsing, recommendation extraction
- [ ] 4.2 TerminologyAdapter: test UMLS concept lookup, RxNorm drug mapping, SNOMED hierarchy traversal
- [ ] 4.3 Test caching behavior for terminology lookups
- [ ] 4.4 Test error handling for missing concepts or expired credentials

## 5. Ingestion Pipeline & Registry Tests

- [ ] 5.1 Test `IngestionRegistry` adapter lookup by document type
- [ ] 5.2 Test pipeline orchestration: select adapter → fetch → validate → ledger update
- [ ] 5.3 Test resume logic: skip completed documents, retry failed documents
- [ ] 5.4 Test ledger state transitions: `PENDING → IN_PROGRESS → COMPLETED | FAILED`
- [ ] 5.5 Test error propagation and dead-letter queue integration

## 6. CLI Command Tests

- [ ] 6.1 Test `ingest --source clinical --ids NCT123,NCT456` with mocked adapter
- [ ] 6.2 Test `ingest resume --ledger-path /tmp/ledger.json`
- [ ] 6.3 Test `ingest status --format json`
- [ ] 6.4 Test CLI error handling (invalid source, missing credentials, network timeout)
- [ ] 6.5 Test CLI output formatting and progress reporting

## 7. Coverage & Validation

- [ ] 7.1 Run `pytest tests/ingestion/ --cov=src/Medical_KG/ingestion --cov-report=term-missing`
- [ ] 7.2 Verify 100% coverage for all adapter modules
- [ ] 7.3 Ensure no network calls in test suite (check for accidental real HTTP requests)
- [ ] 7.4 Document test fixtures and mocking patterns in `tests/ingestion/README.md`
