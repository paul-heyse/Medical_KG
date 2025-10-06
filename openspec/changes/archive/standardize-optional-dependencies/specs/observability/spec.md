# Optional Dependency Handling

## MODIFIED Requirements

### Requirement: Missing Dependency Errors

The system SHALL raise structured, actionable errors when optional dependencies are missing, replacing generic `ModuleNotFoundError`.

#### Scenario: Structured error with install hint

- **WHEN** importing optional package that is not installed
- **THEN** system SHALL raise `MissingDependencyError`
- **AND** error SHALL include feature name being used
- **AND** error SHALL include package name(s) needed
- **AND** error SHALL include install command with extras group
- **AND** error SHALL link to feature documentation if available

#### Scenario: Clear error message format

- **WHEN** `MissingDependencyError` is raised
- **THEN** error message SHALL follow format:

  ```
  Feature '{feature}' requires package '{package}'.
  Install with: pip install medical-kg[{extras}]
  Documentation: {docs_url}
  ```

## ADDED Requirements

### Requirement: Dependency Registry

The system SHALL maintain a registry mapping features to required packages and extras groups.

#### Scenario: Feature to package mapping

- **WHEN** system needs to import optional package
- **THEN** it SHALL look up feature in DEPENDENCY_REGISTRY
- **AND** SHALL retrieve package names and extras group
- **AND** SHALL generate appropriate install hint

#### Scenario: Registry completeness

- **WHEN** adding new optional feature
- **THEN** developer SHALL add entry to DEPENDENCY_REGISTRY
- **AND** SHALL specify packages and extras group
- **AND** SHALL update dependency matrix documentation

### Requirement: Type Safety with Protocol Shims

The system SHALL provide protocol shims for optional packages to enable mypy type checking without requiring installation.

#### Scenario: Protocol shim for optional package

- **WHEN** type checking code that uses optional package
- **THEN** mypy SHALL find protocol shim in stubs directory
- **AND** SHALL type-check usage without package installed
- **AND** SHALL NOT require adding package to ignore_errors

#### Scenario: Reduced mypy suppressions

- **WHEN** protocol shims are implemented
- **THEN** mypy ignore_errors list SHALL be reduced by >50%
- **AND** new code SHALL NOT add to ignore list without justification
- **AND** CI SHALL enforce type checking for optional features

### Requirement: Dependency Matrix Documentation

The system SHALL document all optional dependencies with clear installation instructions.

#### Scenario: Complete dependency matrix

- **WHEN** user needs to know what extras are available
- **THEN** documentation SHALL list all extras groups
- **AND** SHALL explain which features each group enables
- **AND** SHALL provide installation examples
- **AND** SHALL explain how to check installed dependencies

#### Scenario: Diagnostic tooling

- **WHEN** user runs `med dependencies check`
- **THEN** system SHALL list all optional dependency groups
- **AND** SHALL indicate which are installed vs missing
- **AND** SHALL show install commands for missing groups
