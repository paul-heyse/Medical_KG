# Implementation Tasks

## 1. Ingestion Core
- [x] 1.1 Add precise type annotations to `BaseAdapter`, ledger readers/writers, and registry.
- [ ] 1.2 Annotate each clinical/literature/guideline adapter fetch/parse pipeline.
- [ ] 1.3 Provide typed JSON schema loader helpers or stubs for jsonschema usage.

## 2. Catalog & Facets
- [ ] 2.1 Update catalog loaders/pipeline to consume typed `Concept` structures.
- [ ] 2.2 Annotate facets models/generator/router to eliminate `FieldInfo` assignment errors.
- [ ] 2.3 Ensure retrieval clients and neighbor utilities operate on typed DTOs.

## 3. Validation & Tooling
- [ ] 3.1 Install or vendor necessary stub packages (e.g., `types-jsonschema`, OpenSearch client).
- [ ] 3.2 Run `mypy --strict` across `src/Medical_KG/ingestion src/Medical_KG/catalog src/Medical_KG/facets src/Medical_KG/retrieval src/Medical_KG/config src/Medical_KG/ir src/Medical_KG/embeddings src/Medical_KG/security`.
- [ ] 3.3 Execute adapter integration tests (mocked HTTP) and catalog build regression tests.
