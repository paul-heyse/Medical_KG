## ADDED Requirements

### Requirement: Zero Suppressions
The codebase SHALL not use `# type: ignore` (without documented protocol) nor disabling flags in mypy configuration.

#### Scenario: Pull request linting
- **WHEN** mypy runs in CI
- **THEN** it SHALL fail if any new `# type: ignore` or mypy exclusion is introduced without an accompanying protocol definition or justification

### Requirement: Strict Type Checking
All first-party Python modules under `src/Medical_KG` SHALL pass mypy in strict mode (no `ignore_missing_imports`, `implicit_reexport`, or broad excludes).

#### Scenario: Local developer run
- **WHEN** a developer executes `mypy --strict src/Medical_KG`
- **THEN** the command SHALL succeed without errors or warnings

### Requirement: Typed Third-Party Facades
Optional external dependencies (e.g., httpx, locust, torch, tiktoken, spaCy) SHALL be accessed through typed abstractions, stubs, or Protocols to avoid untyped `Any` leakage.

#### Scenario: Optional dependency absent
- **WHEN** a module is imported in an environment without the optional dependency
- **THEN** the typed wrapper SHALL provide fallbacks while retaining accurate type information for mypy

### Requirement: Typed Tests & Fixtures
Test utilities and fixtures SHALL provide explicit annotations so that `mypy --strict tests/...` passes for designated directories.

#### Scenario: Test module addition
- **WHEN** a new test is added under `tests/`
- **THEN** the test SHALL include type annotations for fixtures, mocks, and return values to satisfy mypy strict checks

### Requirement: Contributor Guidance & Enforcement
Documentation SHALL define type safety guidelines and CI SHALL enforce compliance.

#### Scenario: Contributor uptake
- **WHEN** a contributor consults repository docs
- **THEN** they SHALL find guidance on annotations, optional dependency handling, and mypy execution steps
- **AND WHEN** CI runs on the corresponding PR, it SHALL block merges that reduce type safety compliance
