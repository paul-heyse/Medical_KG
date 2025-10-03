## MODIFIED Requirements

### Requirement: Type-Safe Catalog & Facets
The concept catalog pipeline, ontology loaders, and facet indexing SHALL operate on typed structures so strict mypy can guarantee schema correctness.

#### Scenario: Catalog typing
- **WHEN** `mypy --strict src/Medical_KG/catalog src/Medical_KG/facets` runs
- **THEN** loaders, pipeline stages, and facet models SHALL pass without suppressions and produce typed `Concept` and facet payloads used by search/retrieval
- **AND WHEN** catalog build tests run, they SHALL confirm typed payloads serialize to OpenSearch/Neo4j without runtime regressions
