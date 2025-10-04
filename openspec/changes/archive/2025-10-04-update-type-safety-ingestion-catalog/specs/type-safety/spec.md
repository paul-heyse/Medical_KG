## ADDED Requirements

### Requirement: Type-Safe Ingestion & Catalog Pipeline
The ingestion adapters, catalog loaders, and downstream facet/retrieval utilities SHALL be typed end-to-end so strict mypy checks succeed across the ingestion-to-index pipeline.

#### Scenario: Ingestion strict check
- **WHEN** `mypy --strict` runs on `src/Medical_KG/ingestion src/Medical_KG/catalog src/Medical_KG/facets src/Medical_KG/retrieval src/Medical_KG/config src/Medical_KG/ir src/Medical_KG/embeddings src/Medical_KG/security`
- **THEN** it SHALL complete without errors
- **AND WHEN** adapters execute in integration tests
- **THEN** typed signatures SHALL prevent `Any` leakage while preserving existing behaviour
