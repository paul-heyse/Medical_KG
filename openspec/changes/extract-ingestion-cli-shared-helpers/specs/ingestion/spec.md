# Ingestion CLI Shared Helpers

## ADDED Requirements

### Requirement: Shared CLI Helper Module

The ingestion system SHALL provide a shared helper module containing common CLI operations to eliminate code duplication and ensure consistent behavior across CLI implementations.

#### Scenario: NDJSON batch loading

- **WHEN** any CLI needs to load an NDJSON batch file
- **THEN** it SHALL use the shared `load_ndjson_batch()` helper function
- **AND** SHALL receive validated, parsed records
- **AND** SHALL get clear error messages for malformed JSON
- **AND** SHALL NOT implement custom parsing logic

#### Scenario: Adapter invocation

- **WHEN** any CLI needs to invoke an ingestion adapter
- **THEN** it SHALL use the shared `invoke_adapter()` helper function
- **AND** SHALL receive properly configured adapter instances
- **AND** SHALL have consistent error handling for adapter failures
- **AND** SHALL NOT duplicate adapter instantiation logic

#### Scenario: Error formatting

- **WHEN** any CLI needs to display an error message
- **THEN** it SHALL use the shared `format_cli_error()` helper function
- **AND** SHALL produce consistent error message format
- **AND** SHALL include remediation hints where applicable
- **AND** SHALL NOT implement custom error formatting

#### Scenario: Result formatting

- **WHEN** any CLI needs to display ingestion results
- **THEN** it SHALL use the shared `format_results()` helper function
- **AND** SHALL support multiple output formats (text, JSON, table)
- **AND** SHALL include consistent metrics (success/failure counts, timing)
- **AND** SHALL NOT duplicate result formatting logic

#### Scenario: Backward compatibility maintained

- **WHEN** existing CLI implementations are refactored to use shared helpers
- **THEN** CLI behavior SHALL remain identical for end users
- **AND** SHALL NOT introduce breaking changes
- **AND** SHALL pass all existing integration tests
- **AND** output format SHALL remain unchanged
