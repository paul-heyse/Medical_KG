# Implementation Tasks

## 1. Terminology Adapter Type Parameterization

### 1.1 MeSH Adapter

- [x] 1.1.1 Update class declaration: `class MeSHAdapter(HttpAdapter[Any]):`
- [x] 1.1.2 Update `parse()` signature: `def parse(self, raw: Any) -> Document:`
- [x] 1.1.3 Replace `payload = {...}` dict literal with `payload: MeshDocumentPayload = {...}`
- [x] 1.1.4 Verify `Document(raw=payload)` passes type checking

### 1.2 UMLS Adapter

- [x] 1.2.1 Update class declaration: `class UMLSAdapter(HttpAdapter[Any]):`
- [x] 1.2.2 Update `parse()` signature: `def parse(self, raw: Any) -> Document:`
- [x] 1.2.3 Replace dict literal with `payload: UmlsDocumentPayload = {...}`
- [x] 1.2.4 Verify type compatibility with `Document.raw`

### 1.3 LOINC Adapter

- [x] 1.3.1 Update class declaration: `class LoincAdapter(HttpAdapter[Any]):`
- [x] 1.3.2 Update `parse()` signature with typed parameter
- [x] 1.3.3 Use `LoincDocumentPayload` TypedDict
- [x] 1.3.4 Test with existing LOINC fixtures

### 1.4 ICD-11 Adapter

- [x] 1.4.1 Update class declaration: `class Icd11Adapter(HttpAdapter[Any]):`
- [x] 1.4.2 Update `parse()` signature with typed parameter
- [x] 1.4.3 Use `Icd11DocumentPayload` TypedDict
- [x] 1.4.4 Ensure optional field handling (title, definition, uri)

### 1.5 SNOMED Adapter

- [x] 1.5.1 Update class declaration: `class SnomedAdapter(HttpAdapter[Any]):`
- [x] 1.5.2 Update `parse()` signature with typed parameter
- [x] 1.5.3 Use `SnomedDocumentPayload` TypedDict
- [x] 1.5.4 Fix line 246 `document.raw.get("designation")` to use type-safe access

## 2. Literature Adapter Type Parameterization

### 2.1 PubMed Adapter

- [x] 2.1.1 Update class declaration: `class PubMedAdapter(HttpAdapter[Any]):`
- [x] 2.1.2 Update `parse()` signature: `def parse(self, raw: Any) -> Document:`
- [x] 2.1.3 Use `PubMedDocumentPayload` TypedDict with all optional fields marked NotRequired
- [x] 2.1.4 Fix union-attr errors in lines ~53-71 by narrowing JSONValue types
- [x] 2.1.5 Update `validate()` method to handle typed payload (prepare for type guards)

### 2.2 PMC Adapter

- [x] 2.2.1 Update class declaration: `class PmcAdapter(HttpAdapter[Any]):`
- [x] 2.2.2 Update `parse()` signature with typed parameter
- [x] 2.2.3 Use `PmcDocumentPayload` with nested section/media/reference payloads
- [x] 2.2.4 Ensure `_find()` and `_findtext()` helper methods work with typed structures
- [x] 2.2.5 Fix union-attr errors in XML parsing logic

### 2.3 MedRxiv Adapter

- [x] 2.3.1 Update class declaration: `class MedRxivAdapter(HttpAdapter[Any]):`
- [x] 2.3.2 Update `parse()` signature with typed parameter
- [x] 2.3.3 Use `MedRxivDocumentPayload` TypedDict
- [x] 2.3.4 Handle optional `date` field properly

## 3. Type Error Resolution

### 3.1 Fix Terminology Errors

- [x] 3.1.1 Resolve 5 "Missing type parameters" errors (one per adapter)
- [x] 3.1.2 Resolve 5 "Argument 'raw' to Document" errors (typed payload assignment)
- [x] 3.1.3 Verify line 246 union-attr error in SnomedAdapter is fixed

### 3.2 Fix Literature Errors

- [x] 3.2.1 Resolve ~50 union-attr errors by adding JSONValue narrowing helpers
- [x] 3.2.2 Add `ensure_json_mapping()` at fetch boundaries where needed
- [x] 3.2.3 Replace inline `.get()` chains with safer navigation patterns

## 4. Test & Fixture Updates

### 4.1 Fixture Schema Alignment

- [x] 4.1.1 Audit `tests/ingestion/fixtures/terminology.py` - ensure all required fields present
- [x] 4.1.2 Audit `tests/ingestion/fixtures/literature.py` - match TypedDict schemas
- [x] 4.1.3 Add fixtures with optional fields present/absent for each adapter
- [x] 4.1.4 Verify fixture JSON matches TypedDict structure exactly

### 4.2 Test Type Assertions

- [x] 4.2.1 Add `assert isinstance(document.raw, dict)` and verify field access
- [x] 4.2.2 Verify `document.raw["field"]` access works without casting in tests
- [x] 4.2.3 Test that mypy allows direct field access in test code

## 5. Validation & Documentation

### 5.1 Mypy Validation

- [x] 5.1.1 Run `mypy --strict src/Medical_KG/ingestion/adapters/terminology.py`
- [x] 5.1.2 Run `mypy --strict src/Medical_KG/ingestion/adapters/literature.py`
- [x] 5.1.3 Verify error count reduced from ~70 to 0
    - Targeted `mypy --strict` runs now only fail for pre-existing optional dependency gaps (e.g., `fastapi`, `pydantic`); the terminology/literature adapters and fixture modules type-check cleanly.
- [x] 5.1.4 Document any remaining suppressions with inline comments

### 5.2 Documentation Updates

- [x] 5.2.1 Add module docstring to terminology.py explaining typed payload usage
- [x] 5.2.2 Add module docstring to literature.py explaining typed payload usage
- [x] 5.2.3 Update inline comments in parse() methods to reference TypedDict fields
- [x] 5.2.4 Cross-reference `ingestion/types.py` documentation

### 5.3 Integration Testing

- [x] 5.3.1 Run full test suite: `pytest tests/ingestion/`
- [x] 5.3.2 Verify no regressions in adapter behavior
- [x] 5.3.3 Confirm Document.raw populated correctly in integration tests
- [x] 5.3.4 Test with real API responses if bootstrap data available
    - Exercised new optional-field coverage via `pytest -q tests/ingestion/test_adapters.py::test_terminology_optional_field_variants tests/ingestion/test_adapters.py::test_literature_optional_field_variants`.
