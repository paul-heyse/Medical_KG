## MODIFIED Requirements

### Requirement: Subsystem Test Depth

Every subsystem (briefing, ingestion, IR, retrieval, KG, embeddings, security, CLI, config) SHALL have unit and integration tests covering success, failure, and edge cases.

#### Scenario: Briefing regression

- **WHEN** new logic is added to briefing formatters
- **THEN** existing tests SHALL detect regressions in conflict detection, vocabulary redaction, and gap reporting

#### Scenario: PDF table extraction accuracy

- **WHEN** a PDF contains complex tables with merged cells and multi-line content
- **THEN** tests SHALL verify the table is extracted with correct cell boundaries and reading order

#### Scenario: Chunking guardrail enforcement

- **WHEN** a document contains a numbered list spanning multiple potential chunk boundaries
- **THEN** tests SHALL verify the entire list is kept together in a single chunk
