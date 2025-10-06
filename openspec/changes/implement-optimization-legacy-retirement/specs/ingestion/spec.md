## ADDED Requirements
### Requirement: Schema Validation CLI Behaviour
The ingestion CLI demo command SHALL leverage the shared JSON schema adapter and return exit codes consistent with documented behaviour.

#### Scenario: Schema validation success
- **WHEN** a demo batch passes schema validation via CLI options
- **THEN** the command SHALL exit with status 0 and note the validation success

#### Scenario: Schema validation failure
- **WHEN** validation fails
- **THEN** the command SHALL exit with status 2 and include JSON pointer guidance
