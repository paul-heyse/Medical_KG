# Spec Delta: Test Infrastructure (clean-legacy-test-surfaces)

## REMOVED Requirements

### Requirement: Legacy API Test Coverage

**Reason**: Legacy APIs removed from production code

**Migration**: Replace with tests for current API surface

Tests covered deprecated methods like `run_async_legacy()`, string-based ledger states, and fallback coercion.

### Requirement: Compatibility Test Fixtures

**Reason**: Compatibility layers removed

**Migration**: Use current API fixtures only

Fixtures included legacy ledgers, config files, and untyped payloads for testing backwards compatibility.

### Requirement: Legacy Test Helpers

**Reason**: Helpers supported deprecated test patterns

**Migration**: Use current test utilities

Helpers included fixture generators for legacy formats and assertion utilities for deprecated behavior.

## ADDED Requirements

### Requirement: Smoke Test Coverage for Current APIs

The test suite SHALL include smoke tests validating core functionality of current API surface.

#### Scenario: Streaming pipeline smoke test

- **GIVEN** the test suite execution
- **WHEN** streaming pipeline smoke test runs
- **THEN** `stream_events()` API is validated
- **AND** basic event emission is verified
- **AND** test completes successfully

#### Scenario: Enum-only ledger smoke test

- **GIVEN** the test suite execution
- **WHEN** ledger smoke test runs
- **THEN** enum-based state transitions are validated
- **AND** no string coercion is tested
- **AND** test completes successfully

#### Scenario: Typed IR builder smoke test

- **GIVEN** the test suite execution
- **WHEN** IR builder smoke test runs
- **THEN** typed payload processing is validated
- **AND** no fallback coercion is tested
- **AND** test completes successfully

## MODIFIED Requirements

### Requirement: Test Suite Structure

The test suite SHALL focus exclusively on current API surface without legacy compatibility tests.

**Modifications**:

- Removed all legacy API tests
- Deleted obsolete fixtures and helpers
- Added smoke tests for current functionality

#### Scenario: Test suite execution

- **GIVEN** CI pipeline running tests
- **WHEN** full test suite executes
- **THEN** all tests pass
- **AND** no legacy API tests are present
- **AND** coverage meets or exceeds previous levels

#### Scenario: Fixture usage

- **GIVEN** tests requiring fixtures
- **WHEN** fixtures are loaded
- **THEN** only current API fixtures are used
- **AND** no legacy format fixtures exist
- **AND** fixtures reflect production data structures

### Requirement: Test Performance

The test suite SHALL execute efficiently without redundant legacy compatibility tests.

**Modifications**:

- Removed ~260 lines of obsolete tests
- Optimized test execution paths
- Consolidated redundant test cases

#### Scenario: CI test execution time

- **GIVEN** CI pipeline test stage
- **WHEN** tests are executed
- **THEN** execution time is reduced compared to legacy suite
- **AND** no legacy test jobs are present
- **AND** coverage is maintained or improved

#### Scenario: Test coverage reporting

- **GIVEN** test coverage analysis
- **WHEN** coverage reports are generated
- **THEN** coverage focuses on current code paths
- **AND** no legacy code is included in coverage
- **AND** coverage metrics meet project standards
