## MODIFIED Requirements

### Requirement: Subsystem Test Depth

Every subsystem (briefing, ingestion, IR, retrieval, KG, embeddings, security, CLI, config) SHALL have unit and integration tests covering success, failure, and edge cases.

#### Scenario: Briefing regression

- **WHEN** new logic is added to briefing formatters
- **THEN** existing tests SHALL detect regressions in conflict detection, vocabulary redaction, and gap reporting

#### Scenario: Retrieval caching behavior

- **WHEN** a retrieval query is executed multiple times
- **THEN** tests SHALL verify cache hits return identical results without re-executing expensive operations

#### Scenario: Retrieval auth failure

- **WHEN** a retrieval request is made with an expired JWT or invalid API key
- **THEN** tests SHALL verify a 401 Unauthorized response and appropriate error message
