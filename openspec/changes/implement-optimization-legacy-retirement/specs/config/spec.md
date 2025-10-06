## ADDED Requirements
### Requirement: Structured YAML Configuration Loading
The configuration subsystem SHALL load YAML documents used for runtime configuration (pipelines, policies, feature flags) into mapping objects and reject scalar-only payloads.

#### Scenario: Config YAML returns mapping
- **GIVEN** a configuration YAML file containing a top-level mapping
- **WHEN** the loader processes the file
- **THEN** the returned object SHALL be a `dict[str, Any]`
- **AND** non-mapping payloads SHALL raise a `ConfigError` describing the expected structure

#### Scenario: Policy YAML preserves mapping semantics
- **GIVEN** `policy.yaml` contains structured licence tiers
- **WHEN** `ConfigManager` loads policy data
- **THEN** the loader SHALL provide a mapping used to construct `PolicyDocument`
- **AND** tests relying on fixtures SHALL pass with no manual parsing

### Requirement: JSON Schema Validator Adapter
Configuration tooling SHALL expose a JSON schema validation adapter that offers a `validate()` method, integrates with CLI commands, and produces actionable pointer-based errors.

#### Scenario: CLI schema validation success
- **WHEN** a user runs `med config validate --schema config.schema.json config.yaml`
- **THEN** the command SHALL succeed when the payload conforms, using the shared adapter

#### Scenario: CLI schema validation failure messaging
- **WHEN** a payload violates the schema
- **THEN** the CLI SHALL exit with a non-zero status and display JSON pointer guidance sourced from the adapter
