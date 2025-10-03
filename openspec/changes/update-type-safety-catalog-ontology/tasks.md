# Implementation Tasks

## 1. Ontology Input Typing
- [x] 1.1 Create `TypedDict` definitions for each loader input (SNOMED RF2, ICD-11 API, MONDO, HPO, RxNorm, etc.).
- [x] 1.2 Update loader constructors and `load()` generators to accept typed sequences and return `Iterable[Concept]` without `object`.
- [x] 1.3 Adjust normalization utilities to operate on typed payloads (synonym lists, crosswalk maps).

## 2. Catalog Pipeline
- [x] 2.1 Annotate pipeline orchestration (`pipeline.py`, `opensearch.py`, `neo4j.py`, `state.py`) to consume typed concepts and emit typed index/write structures.
- [x] 2.2 Ensure validators/models expose typed fields (no `FieldInfo` assignment issues) and add targeted unit tests covering validation and serialization.
- [x] 2.3 Update OpenSearch/Neo4j fakes in tests to assert typed payloads.

## 3. Facets & Retrieval Integration
- [x] 3.1 Harden facet models/generator/router with explicit types and update tests to cover aggregates and metadata.
- [x] 3.2 Verify retrieval clients (OpenSearch/vector/ontology) operate on typed records when ingesting catalog output.

## 4. Verification
- [x] 4.1 Run `mypy --strict src/Medical_KG/catalog src/Medical_KG/facets` and add the paths to CI enforcement.
- [x] 4.2 Execute catalog build regression tests and facet indexing tests to confirm behavior.
