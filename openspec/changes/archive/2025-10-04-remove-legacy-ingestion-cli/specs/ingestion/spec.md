# Legacy CLI Removal

## REMOVED Requirements

### Requirement: Legacy CLI Support

**Reason**: After successful migration to unified CLI (3+ months), legacy CLI represents technical debt with no user value.

**Migration**: Users must use the unified `med ingest` command. See unified CLI documentation.

**Removed functionality**:

- `med ingest-legacy` command
- Deprecated flag aliases
- Migration warning system
- Legacy entry points

## MODIFIED Requirements

### Requirement: Single CLI Entry Point

The ingestion system SHALL provide **only** the unified command-line interface, with all legacy CLI code removed.

#### Scenario: Only unified CLI available

- **WHEN** a user attempts to run a legacy CLI command
- **THEN** the system SHALL return "command not found" error
- **AND** SHALL NOT provide deprecation warnings (command doesn't exist)
- **AND** SHALL NOT delegate to any compatibility layer

#### Scenario: Simplified codebase

- **WHEN** developers review the CLI codebase
- **THEN** they SHALL find only one CLI implementation
- **AND** SHALL NOT find deprecated code paths
- **AND** SHALL NOT find migration support code
- **AND** tests SHALL cover only the unified CLI

#### Scenario: Clean documentation

- **WHEN** users consult CLI documentation
- **THEN** they SHALL find only unified CLI examples
- **AND** SHALL NOT find migration guides
- **AND** SHALL NOT find deprecated command references
- **AND** SHALL see clear, single-path instructions

## ADDED Requirements

### Requirement: Major Version Breaking Change

The system SHALL treat legacy CLI removal as a major version breaking change requiring appropriate versioning and communication.

#### Scenario: Version bump

- **WHEN** legacy CLI is removed
- **THEN** the package version SHALL be bumped to next major version (e.g., 2.0.0)
- **AND** SHALL be documented in CHANGELOG as breaking change
- **AND** release notes SHALL explicitly list removed commands
- **AND** SHALL provide migration instructions for unmigrated users

#### Scenario: Clear error for unmigrated users

- **WHEN** an unmigrated user tries to use legacy commands
- **THEN** the system SHALL return clear "command not found" error
- **AND** error message SHALL link to unified CLI documentation
- **AND** version upgrade notes SHALL be prominently displayed
- **AND** rollback instructions SHALL be provided in release notes
