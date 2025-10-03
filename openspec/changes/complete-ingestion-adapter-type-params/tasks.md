# Implementation Tasks

## 1. Terminology Adapter Type Parameterization

### 1.1 MeSH Adapter

- [ ] 1.1.1 Update class declaration: `class MeSHAdapter(HttpAdapter[Any]):`
- [ ] 1.1.2 Update `parse()` signature: `def parse(self, raw: Any) -> Document:`
- [ ] 1.1.3 Replace `payload = {...}` dict literal with `payload: MeshDocumentPayload = {...}`
- [ ] 1.1.4 Verify `Document(raw=payload)` passes type checking

### 1.2 UMLS Adapter

- [ ] 1.2.1 Update class declaration: `class UMLSAdapter(HttpAdapter[Any]):`
- [ ] 1.2.2 Update `parse()` signature: `def parse(self, raw: Any) -> Document:`
- [ ] 1.2.3 Replace dict literal with `payload: UmlsDocumentPayload = {...}`
- [ ] 1.2.4 Verify type compatibility with `Document.raw`

### 1.3 LOINC Adapter

- [ ] 1.3.1 Update class declaration: `class LoincAdapter(HttpAdapter[Any]):`
- [ ] 1.3.2 Update `parse()` signature with typed parameter
- [ ] 1.3.3 Use `LoincDocumentPayload` TypedDict
- [ ] 1.3.4 Test with existing LOINC fixtures

### 1.4 ICD-11 Adapter

- [ ] 1.4.1 Update class declaration: `class Icd11Adapter(HttpAdapter[Any]):`
- [ ] 1.4.2 Update `parse()` signature with typed parameter
- [ ] 1.4.3 Use `Icd11DocumentPayload` TypedDict
- [ ] 1.4.4 Ensure optional field handling (title, definition, uri)

### 1.5 SNOMED Adapter

- [ ] 1.5.1 Update class declaration: `class SnomedAdapter(HttpAdapter[Any]):`
- [ ] 1.5.2 Update `parse()` signature with typed parameter
- [ ] 1.5.3 Use `SnomedDocumentPayload` TypedDict
- [ ] 1.5.4 Fix line 246 `document.raw.get("designation")` to use type-safe access

## 2. Literature Adapter Type Parameterization

### 2.1 PubMed Adapter

- [ ] 2.1.1 Update class declaration: `class PubMedAdapter(HttpAdapter[Any]):`
- [ ] 2.1.2 Update `parse()` signature: `def parse(self, raw: Any) -> Document:`
- [ ] 2.1.3 Use `PubMedDocumentPayload` TypedDict with all optional fields marked NotRequired
- [ ] 2.1.4 Fix union-attr errors in lines ~53-71 by narrowing JSONValue types
- [ ] 2.1.5 Update `validate()` method to handle typed payload (prepare for type guards)

### 2.2 PMC Adapter

- [ ] 2.2.1 Update class declaration: `class PmcAdapter(HttpAdapter[Any]):`
- [ ] 2.2.2 Update `parse()` signature with typed parameter
- [ ] 2.2.3 Use `PmcDocumentPayload` with nested section/media/reference payloads
- [ ] 2.2.4 Ensure `_find()` and `_findtext()` helper methods work with typed structures
- [ ] 2.2.5 Fix union-attr errors in XML parsing logic

### 2.3 MedRxiv Adapter

- [ ] 2.3.1 Update class declaration: `class MedRxivAdapter(HttpAdapter[Any]):`
- [ ] 2.3.2 Update `parse()` signature with typed parameter
- [ ] 2.3.3 Use `MedRxivDocumentPayload` TypedDict
- [ ] 2.3.4 Handle optional `date` field properly

## 3. Type Error Resolution

### 3.1 Fix Terminology Errors

- [ ] 3.1.1 Resolve 5 "Missing type parameters" errors (one per adapter)
- [ ] 3.1.2 Resolve 5 "Argument 'raw' to Document" errors (typed payload assignment)
- [ ] 3.1.3 Verify line 246 union-attr error in SnomedAdapter is fixed

### 3.2 Fix Literature Errors

- [ ] 3.2.1 Resolve ~50 union-attr errors by adding JSONValue narrowing helpers
- [ ] 3.2.2 Add `ensure_json_mapping()` at fetch boundaries where needed
- [ ] 3.2.3 Replace inline `.get()` chains with safer navigation patterns

## 4. Test & Fixture Updates

### 4.1 Fixture Schema Alignment

- [ ] 4.1.1 Audit `tests/ingestion/fixtures/terminology.py` - ensure all required fields present
- [ ] 4.1.2 Audit `tests/ingestion/fixtures/literature.py` - match TypedDict schemas
- [ ] 4.1.3 Add fixtures with optional fields present/absent for each adapter
- [ ] 4.1.4 Verify fixture JSON matches TypedDict structure exactly

### 4.2 Test Type Assertions

- [ ] 4.2.1 Add `assert isinstance(document.raw, dict)` and verify field access
- [ ] 4.2.2 Verify `document.raw["field"]` access works without casting in tests
- [ ] 4.2.3 Test that mypy allows direct field access in test code

## 5. Validation & Documentation

### 5.1 Mypy Validation

- [ ] 5.1.1 Run `mypy --strict src/Medical_KG/ingestion/adapters/terminology.py`
- [ ] 5.1.2 Run `mypy --strict src/Medical_KG/ingestion/adapters/literature.py`
- [ ] 5.1.3 Verify error count reduced from ~70 to 0
- [ ] 5.1.4 Document any remaining suppressions with inline comments

### 5.2 Documentation Updates

- [ ] 5.2.1 Add module docstring to terminology.py explaining typed payload usage
- [ ] 5.2.2 Add module docstring to literature.py explaining typed payload usage
- [ ] 5.2.3 Update inline comments in parse() methods to reference TypedDict fields
- [ ] 5.2.4 Cross-reference `ingestion/types.py` documentation

### 5.3 Integration Testing

- [ ] 5.3.1 Run full test suite: `pytest tests/ingestion/`
- [ ] 5.3.2 Verify no regressions in adapter behavior
- [ ] 5.3.3 Confirm Document.raw populated correctly in integration tests
- [ ] 5.3.4 Test with real API responses if bootstrap data available
