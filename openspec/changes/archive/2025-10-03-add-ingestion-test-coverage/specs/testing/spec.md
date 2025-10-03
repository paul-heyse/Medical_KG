## MODIFIED Requirements

### Requirement: Subsystem Test Depth

Every subsystem (briefing, ingestion, IR, retrieval, KG, embeddings, security, CLI, config) SHALL have unit and integration tests covering success, failure, and edge cases.

#### Scenario: Briefing regression

- **WHEN** new logic is added to briefing formatters
- **THEN** existing tests SHALL detect regressions in conflict detection, vocabulary redaction, and gap reporting

#### Scenario: Ingestion adapter failure handling

- **WHEN** an ingestion adapter encounters API rate limiting or malformed responses
- **THEN** tests SHALL verify retry logic, error logging, and ledger state updates without making real network calls

#### Scenario: Ingestion pipeline orchestration

- **WHEN** the ingestion pipeline processes a batch of documents
- **THEN** tests SHALL verify adapter selection, document transformation, ledger updates, and resume functionality using mocked external dependencies
