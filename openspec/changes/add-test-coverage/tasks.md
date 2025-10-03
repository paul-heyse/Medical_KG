# Implementation Tasks

## 1. Test Suite Stabilization
- [ ] 1.1 Export missing test utilities (e.g., InMemoryBriefingRepository)
- [x] 1.2 Bundle schema references locally to avoid external fetches
- [ ] 1.3 Mock external dependencies (NCBI, Kafka, OpenSearch, GPUs)
- [ ] 1.4 Fix flaky assertions & nondeterministic randomness
- [ ] 1.5 Document required secrets and provide defaults for tests

## 2. Coverage Gap Analysis
- [ ] 2.1 Generate per-module coverage report
- [ ] 2.2 Catalog untested files/functions
- [ ] 2.3 Prioritize high-risk/high-complexity areas

## 3. Unit & Integration Tests
- [x] 3.1 Briefing service & formatters edge cases
- [x] 3.2 IR builder/validator schema validations
- [ ] 3.3 Ingestion adapters (clinical, guidelines, literature, terminology)
- [ ] 3.4 Retrieval service (auth, caching, ranking fallbacks)
- [ ] 3.5 Security modules (license enforcement, retention policies)
- [x] 3.6 CLI commands & failure paths
- [ ] 3.7 Embeddings GPU validator scenarios
- [ ] 3.8 KG writer & validators

## 4. Test Infrastructure
- [ ] 4.1 Shared fixtures (factories, sample documents, responses)
- [ ] 4.2 Async test helpers & transport mocks
- [ ] 4.3 Fake service implementations for integration-style tests

## 5. Coverage Enforcement
- [ ] 5.1 Add pytest coverage config (min-percent 95%)
- [ ] 5.2 Integrate coverage check into CI pipeline
- [ ] 5.3 Publish HTML/XML reports as artifacts
- [ ] 5.4 Add coverage badge/dashboard

## 6. Documentation & Guidelines
- [x] 6.1 Testing strategy doc (unit vs integration vs e2e)
- [x] 6.2 Contributor guide for adding tests
- [x] 6.3 Maintenance plan (triage failing tests, update fixtures)

## 7. Validation
- [ ] 7.1 Verify ≥95% coverage with pytest --cov
- [ ] 7.2 Run full suite in CI environment
- [ ] 7.3 Track coverage regressions automatically
