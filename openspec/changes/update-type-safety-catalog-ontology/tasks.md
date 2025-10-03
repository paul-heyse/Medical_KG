# Implementation Tasks

## 1. Ontology Input Typing
- [ ] 1.1 Create `TypedDict` definitions for each loader input (SNOMED RF2, ICD-11 API, MONDO, HPO, RxNorm, etc.).
- [ ] 1.2 Update loader constructors and `load()` generators to accept typed sequences and return `Iterable[Concept]` without `object`.
- [ ] 1.3 Adjust normalization utilities to operate on typed payloads (synonym lists, crosswalk maps).

## 2. Catalog Pipeline
- [ ] 2.1 Annotate pipeline orchestration (`pipeline.py`, `opensearch.py`, `neo4j.py`, `state.py`) to consume typed concepts and emit typed index/write structures.
- [ ] 2.2 Ensure validators/models expose typed fields (no `FieldInfo` assignment issues) and add targeted unit tests covering validation and serialization.
- [ ] 2.3 Update OpenSearch/Neo4j fakes in tests to assert typed payloads.

## 3. Facets & Retrieval Integration
- [ ] 3.1 Harden facet models/generator/router with explicit types and update tests to cover aggregates and metadata.
- [ ] 3.2 Verify retrieval clients (OpenSearch/vector/ontology) operate on typed records when ingesting catalog output.

## 4. Verification
- [ ] 4.1 Run `mypy --strict src/Medical_KG/catalog src/Medical_KG/facets` and add the paths to CI enforcement.
- [ ] 4.2 Execute catalog build regression tests and facet indexing tests to confirm behavior.
