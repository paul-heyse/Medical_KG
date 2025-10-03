## Why
Catalog loaders currently accept loosely typed records and rely on runtime duck typing for ontology fields, which leads to unsafe constructs (e.g., iterating over `object`). The catalog pipeline, validators, and facet indexing code still use untyped dictionaries, making it difficult to reason about concept provenance and vector indexing. Splitting this work from the ingestion base change enables concentrated effort on catalog and facet typing.

## What Changes
- Define typed structures for ontology inputs (SNOMED, ICD-11, MONDO, HPO, RxNorm, etc.) and ensure loaders emit strictly typed `Concept` objects.
- Annotate catalog pipeline stages (normalization, OpenSearch writes, Neo4j integration) with typed DTOs and remove `object` fallbacks.
- Tighten facet models/generator/router to avoid `FieldInfo` assignment errors and align with typed facet schemas.
- Expand tests to cover typed loaders and ensure facet payloads roundtrip through OpenSearch & Neo4j fakes.
- Enforce strict mypy for `src/Medical_KG/catalog` and `src/Medical_KG/facets` modules in CI.

## Impact
- **Specs**: `type-safety`
- **Code**: `src/Medical_KG/catalog/**`, `src/Medical_KG/facets/**`, `tests/catalog/**`, `tests/facets/**`
- **Tooling**: May require adding or updating stubs for RDF/SPARQL/OpenSearch clients
- **Risks**: Schema drift in catalog normalization or facet indexing; mitigated via integration tests
