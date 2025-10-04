## MODIFIED Requirements

### Requirement: Zero Suppressions

The codebase SHALL not use `# type: ignore` (without documented protocol) nor disabling flags in mypy configuration.

#### Scenario: Core service typing

- **WHEN** mypy runs in CI against `config`, `ingestion`, `retrieval`, and `kg` modules
- **THEN** it SHALL report zero suppressions or `Any` fallbacks introduced by these systems

### Requirement: Strict Type Checking

All first-party Python modules under `src/Medical_KG` SHALL pass mypy in strict mode (no `ignore_missing_imports`, `implicit_reexport`, or broad excludes).

#### Scenario: Service layer audit

- **WHEN** a developer executes `mypy --strict src/Medical_KG/config src/Medical_KG/ingestion src/Medical_KG/retrieval src/Medical_KG/kg`
- **THEN** the command SHALL succeed without errors or warnings
