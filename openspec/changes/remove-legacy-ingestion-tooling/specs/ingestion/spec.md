# Spec Delta: Ingestion Tooling (remove-legacy-ingestion-tooling)

## REMOVED Requirements

### Requirement: Legacy CLI Migration Scripts

**Reason**: CLI migration completed with >95% adoption of unified CLI

**Migration**: N/A - scripts were for one-time migration only

Migration scripts assisted in transitioning from dual CLI interfaces to the unified `med ingest` command.

### Requirement: CLI Migration Validation Tooling

**Reason**: No longer needed after successful migration

**Migration**: Use unified CLI directly without validation scripts

Validation tooling checked for legacy CLI usage and verified unified CLI adoption metrics.

### Requirement: Legacy CLI Documentation

**Reason**: Legacy CLI no longer exists

**Migration**: Reference archived documentation for historical context only

Documentation included migration guides, compatibility matrices, and command comparisons.

## MODIFIED Requirements

### Requirement: Ingestion CLI Documentation

The ingestion system SHALL provide documentation and tooling exclusively for the unified CLI interface.

**Modifications**:

- Removed legacy CLI references and migration guides
- Archived migration timeline and historical documentation
- Updated all examples to use unified CLI

#### Scenario: CLI documentation references

- **GIVEN** a developer reading CLI documentation
- **WHEN** they access `docs/ingestion_runbooks.md`
- **THEN** all examples use `med ingest <adapter>` syntax
- **AND** no legacy CLI commands are referenced
- **AND** migration guides are linked from archive only

#### Scenario: Operations guide CLI usage

- **GIVEN** an operator following runbook procedures
- **WHEN** they execute CLI commands
- **THEN** all commands use the unified CLI interface
- **AND** no "if using legacy CLI" conditionals exist
- **AND** troubleshooting covers unified CLI only

### Requirement: Development Tooling

The project SHALL maintain development and operational tooling for the current CLI interface only.

**Modifications**:

- Removed migration-specific scripts and helpers
- Cleaned CI/CD pipelines of legacy CLI test jobs

#### Scenario: CI testing

- **GIVEN** a pull request triggering CI
- **WHEN** CLI integration tests run
- **THEN** only unified CLI is tested
- **AND** no legacy CLI validation occurs
- **AND** test results reflect current interface

#### Scenario: Script execution

- **GIVEN** a developer running ingestion scripts
- **WHEN** they use scripts in `scripts/` directory
- **THEN** no migration scripts are present
- **AND** all scripts use unified CLI interface
- **AND** no legacy command wrappers exist
