## MODIFIED Requirements

### Requirement: Subsystem Test Depth

Every subsystem (briefing, ingestion, IR, retrieval, KG, embeddings, security, CLI, config) SHALL have unit and integration tests covering success, failure, and edge cases.

#### Scenario: Briefing regression

- **WHEN** new logic is added to briefing formatters
- **THEN** existing tests SHALL detect regressions in conflict detection, vocabulary redaction, and gap reporting

#### Scenario: KG constraint violation

- **WHEN** a KG write operation violates a uniqueness constraint
- **THEN** tests SHALL verify the operation is rejected, an error is logged, and the transaction is rolled back

#### Scenario: Embeddings GPU fallback

- **WHEN** GPU is unavailable or encounters a CUDA error
- **THEN** tests SHALL verify the embeddings service falls back to CPU and logs a warning
