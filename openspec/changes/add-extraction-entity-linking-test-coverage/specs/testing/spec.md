## MODIFIED Requirements

### Requirement: Subsystem Test Depth

Every subsystem (briefing, ingestion, IR, retrieval, KG, embeddings, security, CLI, config) SHALL have unit and integration tests covering success, failure, and edge cases.

#### Scenario: Briefing regression

- **WHEN** new logic is added to briefing formatters
- **THEN** existing tests SHALL detect regressions in conflict detection, vocabulary redaction, and gap reporting

#### Scenario: Extraction parser accuracy

- **WHEN** a clinical text snippet contains a confidence interval, p-value, or count
- **THEN** tests SHALL verify the parser correctly extracts and normalizes the values

#### Scenario: Entity linking disambiguation

- **WHEN** an entity has multiple candidate concepts with similar confidence scores
- **THEN** tests SHALL verify the LLM-based disambiguator selects the most contextually appropriate concept
