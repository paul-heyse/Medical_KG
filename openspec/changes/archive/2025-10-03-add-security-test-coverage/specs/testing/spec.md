## MODIFIED Requirements

### Requirement: Subsystem Test Depth

Every subsystem (briefing, ingestion, IR, retrieval, KG, embeddings, security, CLI, config) SHALL have unit and integration tests covering success, failure, and edge cases.

#### Scenario: Briefing regression

- **WHEN** new logic is added to briefing formatters
- **THEN** existing tests SHALL detect regressions in conflict detection, vocabulary redaction, and gap reporting

#### Scenario: License tier enforcement

- **WHEN** a user with a "free" license tier requests premium content
- **THEN** tests SHALL verify the content is redacted or access is denied per policy

#### Scenario: Retention policy execution

- **WHEN** a retention policy is executed
- **THEN** tests SHALL verify data older than the retention period is anonymized or deleted, and audit logs are preserved
