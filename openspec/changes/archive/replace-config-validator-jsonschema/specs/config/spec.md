# Configuration Validation

## MODIFIED Requirements

### Requirement: Configuration Schema Validation

The configuration system SHALL use `jsonschema` library for schema validation, replacing custom validator implementation.

#### Scenario: JSON Schema compliance

- **WHEN** validating configuration files
- **THEN** the system SHALL use `jsonschema` library with Draft 7 dialect
- **AND** SHALL support full JSON Schema features (oneOf, anyOf, if/then/else, $ref)
- **AND** SHALL NOT use custom validation logic for standard features

#### Scenario: Clear error messages

- **WHEN** configuration validation fails
- **THEN** error message SHALL include JSON pointer to error location
- **AND** SHALL include actual value that failed validation
- **AND** SHALL include expected constraint (type, range, enum values)
- **AND** SHALL provide remediation hint where applicable

## ADDED Requirements

### Requirement: Schema Versioning

Configuration schemas SHALL include version metadata for compatibility tracking and migration.

#### Scenario: Schema version declaration

- **WHEN** authoring a configuration schema
- **THEN** it SHALL include `version` field (e.g., "1.2")
- **AND** SHALL include `$schema` field referencing JSON Schema draft

#### Scenario: Version compatibility checking

- **WHEN** loading a configuration file
- **THEN** the system SHALL check schema version compatibility
- **WHEN** config uses unsupported schema version
- **THEN** the system SHALL emit warning or error (configurable)
- **AND** SHALL document migration path to current version

### Requirement: Custom Format Validators

The configuration system SHALL support domain-specific format validators beyond JSON Schema standard formats.

#### Scenario: Duration format validation

- **WHEN** schema specifies `"format": "duration"`
- **THEN** validator SHALL accept strings like "5m", "1h", "2d"
- **AND** SHALL reject invalid duration formats

#### Scenario: Adapter name format validation

- **WHEN** schema specifies `"format": "adapter_name"`
- **THEN** validator SHALL check adapter exists in registry
- **AND** SHALL reject unknown adapter names

#### Scenario: Custom format documentation

- **WHEN** developers need to use custom formats
- **THEN** documentation SHALL list all custom formats
- **AND** SHALL provide examples for each format
- **AND** SHALL explain validation rules
