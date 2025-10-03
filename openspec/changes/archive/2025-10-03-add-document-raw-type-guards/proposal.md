# Add Document.raw Type Guards

## Why

8 adapter `validate()` methods currently perform runtime `isinstance(document.raw, Mapping)` checks before indexing into the raw payload, defeating the benefits of TypedDict contracts. This runtime coupling prevents static analysis from catching schema mismatches and forces developers to reason about types at runtime rather than compile-time. Type guards will enable static narrowing while preserving runtime safety.

## What Changes

- Introduce type guard helper functions in `src/Medical_KG/ingestion/types.py` for each payload family union:
  - `is_terminology_payload(raw: DocumentRaw | None) -> TypeGuard[TerminologyDocumentPayload]`
  - `is_literature_payload(raw: DocumentRaw | None) -> TypeGuard[LiteratureDocumentPayload]`
  - `is_clinical_payload(raw: DocumentRaw | None) -> TypeGuard[ClinicalCatalogDocumentPayload]`
  - `is_guideline_payload(raw: DocumentRaw | None) -> TypeGuard[GuidelineDocumentPayload]`
  - `is_knowledge_base_payload(raw: DocumentRaw | None) -> TypeGuard[KnowledgeBaseDocumentPayload]`
- Add fine-grained type guards for specific adapters where needed (e.g., `is_pubmed_payload()`)
- Refactor 8 adapter `validate()` methods to use type guards instead of `isinstance(raw, Mapping)` checks
- Remove defensive `if isinstance(raw, Mapping)` patterns throughout adapters

## Impact

- **Affected specs**: `ingestion` (adds Type Guard requirement)
- **Affected code**:
  - `src/Medical_KG/ingestion/types.py` (~80 new lines for type guards)
  - `src/Medical_KG/ingestion/adapters/literature.py` (3 validate methods)
  - `src/Medical_KG/ingestion/adapters/terminology.py` (1 validate method, line 246)
  - `src/Medical_KG/ingestion/adapters/clinical.py` (1 validate method, line 225)
  - `tests/ingestion/test_adapters.py` (type guard tests)
- **Benefits**: Static type narrowing, eliminates runtime isinstance checks, improves error messages
- **Coordination**: Depends on `complete-ingestion-adapter-type-params` being completed first
