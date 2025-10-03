# Unified Ingestion CLI Interface

## ADDED Requirements

### Requirement: Single CLI Entry Point

The ingestion system SHALL provide a single, unified command-line interface for all ingestion operations, replacing the parallel legacy and modern CLIs.

#### Scenario: Unified command structure

- **WHEN** a user runs `med ingest <adapter> [options]`
- **THEN** the system SHALL invoke the specified adapter with the given options
- **AND** SHALL support all features from both legacy and modern CLIs
- **AND** SHALL use shared CLI helpers for consistent behavior
- **AND** SHALL provide clear help text and examples

#### Scenario: Batch processing

- **WHEN** a user runs `med ingest <adapter> --batch file.ndjson`
- **THEN** the system SHALL load and process the NDJSON batch file
- **AND** SHALL validate each record
- **AND** SHALL report success/failure counts
- **AND** SHALL support `--resume` for ledger-based continuation

#### Scenario: Auto mode fetching

- **WHEN** a user runs `med ingest <adapter> --auto [--limit N]`
- **THEN** the system SHALL automatically fetch records from the adapter source
- **AND** SHALL respect rate limits and pagination
- **AND** SHALL support date range filtering
- **AND** SHALL show progress during fetch

#### Scenario: Output format selection

- **WHEN** a user specifies `--output json|text|table`
- **THEN** the system SHALL format output in the requested format
- **AND** SHALL produce machine-readable JSON for scripts
- **AND** SHALL produce human-readable text for terminal use
- **AND** SHALL produce structured tables for reports

### Requirement: Backward-Compatible Deprecation

The system SHALL provide backward-compatible command delegates during a migration period, warning users to adopt the unified CLI.

#### Scenario: Legacy command deprecation

- **WHEN** a user runs a deprecated legacy command
- **THEN** the system SHALL display a deprecation warning
- **AND** SHALL delegate to the unified CLI
- **AND** SHALL translate legacy flags to unified flags
- **AND** SHALL function identically to the original command
- **AND** SHALL log usage for tracking

#### Scenario: Migration assistance

- **WHEN** a user needs to migrate from old CLI
- **THEN** the system SHALL provide clear error messages with migration hints
- **AND** SHALL link to migration documentation
- **AND** SHALL suggest equivalent unified commands
- **AND** SHALL allow suppressing warnings via environment variable

### Requirement: Enhanced User Experience

The unified CLI SHALL provide superior user experience through progress reporting, clear errors, and comprehensive help.

#### Scenario: Progress reporting

- **WHEN** processing large batches in a terminal (TTY)
- **THEN** the system SHALL display a progress bar
- **AND** SHALL show current record being processed
- **AND** SHALL display success/failure counters
- **AND** SHALL calculate and show ETA
- **AND** SHALL auto-disable in non-TTY environments (pipes)

#### Scenario: Error clarity

- **WHEN** an error occurs during ingestion
- **THEN** the system SHALL categorize the error (user/data/system)
- **AND** SHALL provide remediation hints for common errors
- **AND** SHALL set appropriate exit codes (0=success, 1=error, 2=invalid usage)
- **AND** SHALL show stack traces only in verbose mode

#### Scenario: Comprehensive help

- **WHEN** a user runs `med ingest --help`
- **THEN** the system SHALL display command overview
- **AND** SHALL list all available adapters
- **AND** SHALL show all flags and options with descriptions
- **AND** SHALL include usage examples
- **AND** SHALL link to online documentation
