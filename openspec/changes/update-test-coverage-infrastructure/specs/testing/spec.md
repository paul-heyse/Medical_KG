## ADDED Requirements

### Requirement: Typed Test Infrastructure

The test suite SHALL provide shared typed fixtures, async mocks, and service doubles so new tests can rely on annotated utilities instead of ad-hoc stubs.

#### Scenario: New integration test

- **WHEN** a contributor writes an integration test for ingestion or retrieval
- **THEN** they SHALL be able to import typed factories and doubles from `tests/common` without introducing `Any` usage

### Requirement: Pragmatic Coverage Enforcement

Coverage enforcement SHALL use pytest’s coverage tooling with agreed thresholds and reports instead of manual tracing requiring 100% line execution.

#### Scenario: CI coverage gate

- **WHEN** a pull request runs CI
- **THEN** coverage SHALL be evaluated using pytest-cov thresholds and SHALL fail only if targets are not met
- **AND** HTML/XML reports SHALL be produced for inspection and uploaded as build artifacts
