## ADDED Requirements

### Requirement: Type-Safe Extraction Layer
The extraction stack SHALL expose typed models and services such that strict mypy checks succeed across `src/Medical_KG/extraction`.

#### Scenario: Extraction strict check
- **WHEN** `mypy --strict src/Medical_KG/extraction` runs in CI
- **THEN** it SHALL report zero errors
- **AND WHEN** extraction payloads are written to the knowledge graph
- **THEN** they SHALL be validated against typed interfaces without resorting to `Any`
