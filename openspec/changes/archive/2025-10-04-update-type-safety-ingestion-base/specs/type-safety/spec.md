## MODIFIED Requirements

### Requirement: Type-Safe Ingestion Core
The ingestion adapters, CLI, and shared utilities SHALL expose typed payloads and state transitions so strict mypy checks succeed without `Any` leakage.

#### Scenario: Adapter payload typing
- **WHEN** `mypy --strict src/Medical_KG/ingestion` runs
- **THEN** the ClinicalTrials, openFDA, DailyMed, literature, terminology, and guideline adapters SHALL type-check without suppressions and emit `Document` objects backed by typed payloads
- **AND WHEN** ingestion CLI commands execute in tests, they SHALL operate over typed registries and ledgers without runtime regressions
