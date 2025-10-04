## ADDED Requirements

### Requirement: Comprehensive Test Coverage
The project SHALL maintain at least 95% statement coverage across all production modules under `src/Medical_KG` using automated testing.

#### Scenario: Coverage gate
- **WHEN** the test suite runs in CI
- **THEN** coverage SHALL be measured and MUST meet or exceed 95% for total statements, otherwise the pipeline SHALL fail

### Requirement: Deterministic Test Suite
Tests SHALL run deterministically without external network access or secret dependencies.

#### Scenario: Offline execution
- **WHEN** tests run on a clean environment without network or secrets
- **THEN** all external calls SHALL be mocked or stubbed, and tests SHALL pass using bundled fixtures

### Requirement: Subsystem Test Depth
Every subsystem (briefing, ingestion, IR, retrieval, KG, embeddings, security, CLI, config) SHALL have unit and integration tests covering success, failure, and edge cases.

#### Scenario: Briefing regression
- **WHEN** new logic is added to briefing formatters
- **THEN** existing tests SHALL detect regressions in conflict detection, vocabulary redaction, and gap reporting

### Requirement: Coverage Reporting & Enforcement
Coverage results SHALL be published as artifacts and enforced by tooling.

#### Scenario: Coverage report
- **WHEN** the test suite completes
- **THEN** an HTML/XML coverage report SHALL be generated and uploaded, and the coverage target SHALL be enforced in CI

### Requirement: Test Infrastructure & Documentation
The project SHALL provide shared fixtures, factories, and guides to support ongoing test authoring and maintenance.

#### Scenario: New contributor
- **WHEN** a contributor adds tests for a module
- **THEN** they SHALL have access to documented fixtures/helpers and guidance on mocking patterns and coverage expectations
