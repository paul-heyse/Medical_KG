## ADDED Requirements

### Requirement: Shared Test Fixtures

The test suite SHALL provide centralized, reusable fixtures for common test objects (documents, chunks, facets, users, API responses) to reduce boilerplate and improve test maintainability.

#### Scenario: Adding tests for a new module

- **WHEN** a developer writes tests for a new module
- **THEN** they SHALL be able to use `document_factory`, `chunk_factory`, `facet_factory`, and other fixtures from `conftest.py` without reimplementing them

### Requirement: Async Test Support

The test suite SHALL provide helpers for testing async code (FastAPI endpoints, async services, async iterators) to ensure consistent patterns across the codebase.

#### Scenario: Testing an async endpoint

- **WHEN** a developer tests a FastAPI endpoint that performs async operations
- **THEN** they SHALL use `async_test_client` and `mock_async_iterator` helpers to simulate async behavior without real external calls

### Requirement: Fake Service Implementations

The test suite SHALL provide fake implementations of external services (Neo4j, OpenSearch, Kafka, LLMs) for integration-style tests that verify end-to-end flows without real infrastructure.

#### Scenario: Integration test for KG write → index → search flow

- **WHEN** a test verifies the full pipeline from KG write to OpenSearch indexing
- **THEN** it SHALL use `FakeNeo4jService` and `FakeOpenSearchService` to simulate the full flow in-memory

## ADDED Requirements

### Requirement: Coverage Reporting & Enforcement

Coverage results SHALL be published as artifacts and enforced by tooling.

#### Scenario: Coverage report

- **WHEN** the test suite completes
- **THEN** an HTML/XML coverage report SHALL be generated and uploaded, and the coverage target SHALL be enforced in CI

#### Scenario: Coverage regression

- **WHEN** a PR reduces overall coverage below 95%
- **THEN** the CI pipeline SHALL fail and block the merge

### Requirement: Test Infrastructure Documentation

The project SHALL provide comprehensive documentation on test infrastructure, fixtures, mocking patterns, and contribution guidelines.

#### Scenario: New contributor

- **WHEN** a contributor adds tests for a module
- **THEN** they SHALL have access to documented fixtures/helpers and guidance on mocking patterns and coverage expectations
