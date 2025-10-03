## MODIFIED Requirements

### Requirement: Typed Third-Party Facades

Optional external dependencies (e.g., httpx, locust, torch, tiktoken, spaCy) SHALL be accessed through typed abstractions, stubs, or Protocols to avoid untyped `Any` leakage.

#### Scenario: Optional dependency wrapper

- **WHEN** a developer imports optional dependencies through `utils/optional_dependencies`
- **THEN** the returned objects SHALL conform to defined Protocols with typed fallbacks even when the dependency is missing at runtime

### Requirement: Typed Tests & Fixtures

Test utilities and fixtures SHALL provide explicit annotations so that `mypy --strict tests/...` passes for designated directories.

#### Scenario: Fixture usage

- **WHEN** tests under `tests/` use shared fixtures or async helpers
- **THEN** those fixtures SHALL expose annotated return types allowing mypy strict checks to pass without additional ignores
