# Type Guards for Document.raw - Design Document

## Context

Adapters currently use runtime `isinstance(document.raw, Mapping)` checks in `validate()` methods before accessing payload fields. This defeats TypedDict benefits and prevents static analysis from verifying schema correctness. Type guards enable compile-time type narrowing while preserving runtime safety.

## Goals

- Replace 8 runtime isinstance checks with type guards
- Enable static type narrowing in validate() methods
- Provide reusable type guards for all payload families
- Maintain runtime safety without performance impact

## Non-Goals

- Runtime payload validation (that's ingestion's job)
- Changing Document.raw type to be more specific (keep union flexibility)
- Adding payload introspection or reflection

## Technical Decisions

### Decision 1: Family-Level Type Guards

**Chosen**: Define type guards for each payload family union:

```python
def is_terminology_payload(raw: DocumentRaw | None) -> TypeGuard[TerminologyDocumentPayload]:
    if raw is None:
        return False
    return isinstance(raw, dict) and (
        "descriptor_id" in raw  # MeSH
        or "cui" in raw  # UMLS
        or ("code" in raw and ("display" in raw or "property" in raw))  # LOINC/SNOMED
    )
```

**Rationale**:

- Matches existing payload family structure in types.py
- Enables broad narrowing without adapter-specific coupling
- Reusable across multiple adapters in same family

**Alternatives Considered**:

- Adapter-specific guards (e.g., `is_mesh_payload`): More granular but 18 functions vs 5
- Single `is_valid_payload` guard: Too coarse, doesn't help narrowing
- No guards, use assert/cast: Defeats type safety, no compile-time help

### Decision 2: Structural Typing for Guard Implementation

**Chosen**: Check for discriminating fields rather than type instances:

```python
def is_literature_payload(raw: DocumentRaw | None) -> TypeGuard[LiteratureDocumentPayload]:
    if raw is None:
        return False
    return isinstance(raw, dict) and (
        "pmid" in raw  # PubMed
        or "pmcid" in raw  # PMC
        or "doi" in raw  # MedRxiv
    )
```

**Rationale**:

- TypedDict has no runtime type to check
- Structural checks align with duck typing philosophy
- Fast: O(1) dict key lookups

**Alternatives Considered**:

- Check all required fields: Expensive, redundant with validation
- Use `__annotations__`: Runtime introspection overhead
- Pattern matching: Requires Python 3.10+, overkill for simple checks

### Decision 3: Graceful None Handling

**Chosen**: All type guards return False for None, never raise

**Rationale**:

- Document.raw is Optional (can be None)
- Adapters should always populate raw, but guard is defensive
- Explicit None checks clearer than relying on isinstance behavior

**Pattern**:

```python
def validate(self, document: Document) -> None:
    raw = document.raw
    if not is_pubmed_payload(raw):
        raise ValueError("PubMedAdapter produced non-PubMed payload")
    # mypy now knows raw is PubMedDocumentPayload
    if not PMID_RE.match(str(raw["pmid"])):
        raise ValueError("Invalid PMID")
```

## Implementation Strategy

### Phase 1: Type Guard Functions (Day 1)

**Location**: `src/Medical_KG/ingestion/types.py` (collocated with TypedDicts)

**Functions**:

1. `is_terminology_payload()` - checks for MeSH/UMLS/LOINC/ICD-11/SNOMED fields
2. `is_literature_payload()` - checks for PMID/PMCID/DOI
3. `is_clinical_payload()` - checks for NCT ID/device IDs
4. `is_guideline_payload()` - checks for guideline UIDs
5. `is_knowledge_base_payload()` - checks for knowledge base identifiers

**Testing**: Unit tests verify:

- Guards return True for valid payloads
- Guards return False for None
- Guards return False for mismatched payloads
- Mypy accepts narrowed type in test code

### Phase 2: Adapter Refactoring (Days 2-3)

**Order**:

1. Literature adapters (3) - most complex validation logic
2. Terminology adapters (1) - simpler, good for pattern validation
3. Clinical adapters (1) - medium complexity

**Pattern**:

```python
# Before
def validate(self, document: Document) -> None:
    raw = document.raw
    pmid = raw["pmid"] if isinstance(raw, Mapping) else None
    if not isinstance(pmid, (str, int)) or not PMID_RE.match(str(pmid)):
        raise ValueError("Invalid PMID")

# After
def validate(self, document: Document) -> None:
    raw = document.raw
    assert is_pubmed_payload(raw), "PubMedAdapter produced non-PubMed payload"
    if not PMID_RE.match(str(raw["pmid"])):
        raise ValueError("Invalid PMID")
```

### Phase 3: Fine-Grained Guards (Optional, Day 4)

If family-level guards prove insufficient, add adapter-specific guards:

```python
def is_pubmed_payload(raw: DocumentRaw | None) -> TypeGuard[PubMedDocumentPayload]:
    return isinstance(raw, dict) and "pmid" in raw and "abstract" in raw
```

## Type Guard Implementation Details

### Discriminating Fields by Family

**Terminology**:

- MeSH: `descriptor_id`
- UMLS: `cui`
- LOINC: `code` + `property`/`system`/`method`
- ICD-11: `code` + optional `title`/`definition`
- SNOMED: `code` + `designation`

**Literature**:

- PubMed: `pmid` + `abstract`
- PMC: `pmcid` + `sections`
- MedRxiv: `doi` + `abstract`

**Clinical**:

- ClinicalTrials: `nct_id` + `arms`/`eligibility`
- OpenFDA: `identifier` + `record`
- DailyMed: `setid` + `sections`

**Guidelines**:

- NICE: `uid` + `summary`
- USPSTF: `id` + `title` + `status`

**Knowledge Base**:

- CDC Socrata: `identifier` + `record`
- CDC WONDER: `rows`
- WHO GHO: `value` + optional `indicator`/`country`
- OpenPrescribing: `identifier` + `record`

### Performance Considerations

Type guards are O(1):

- Single `isinstance(raw, dict)` check
- 1-3 `in` dict operations (hashed lookups)
- No iteration or deep inspection

Negligible overhead vs current isinstance checks.

## Migration Path

### For Each Adapter validate() Method

**Step 1**: Add type guard assertion at top
**Step 2**: Remove isinstance checks
**Step 3**: Update field access to use direct indexing
**Step 4**: Run mypy to verify narrowing works
**Step 5**: Test runtime behavior unchanged

### Example Migration

```python
# SnomedAdapter.validate() - Line 242
# BEFORE:
def validate(self, document: Document) -> None:
    code = document.metadata.get("code")
    if not isinstance(code, str) or not _SNOMED_RE.match(code):
        raise ValueError("Invalid SNOMED CT code")
    if not document.raw.get("designation"):  # Line 246 - union-attr error
        raise ValueError("SNOMED record missing designation list")

# AFTER:
def validate(self, document: Document) -> None:
    code = document.metadata.get("code")
    if not isinstance(code, str) or not _SNOMED_RE.match(code):
        raise ValueError("Invalid SNOMED CT code")
    raw = document.raw
    assert is_snomed_payload(raw), "SnomedAdapter produced non-SNOMED payload"
    if not raw.get("designation"):  # mypy now knows raw is SnomedDocumentPayload
        raise ValueError("SNOMED record missing designation list")
```

## Testing Strategy

### Unit Tests for Type Guards

**File**: `tests/ingestion/test_type_guards.py`

```python
def test_is_terminology_payload_mesh():
    payload: MeshDocumentPayload = {"name": "test", "terms": [], "descriptor_id": "D000001"}
    assert is_terminology_payload(payload)

def test_is_terminology_payload_none():
    assert not is_terminology_payload(None)

def test_is_terminology_payload_wrong_family():
    payload: PubMedDocumentPayload = {"pmid": "12345", "title": "test", ...}
    assert not is_terminology_payload(payload)
```

### Adapter Validation Tests

**File**: `tests/ingestion/test_adapters.py` (existing)

Add assertions that type guards work in validate():

```python
def test_pubmed_validation_with_type_guard(pubmed_adapter, pubmed_document):
    # Should not raise
    pubmed_adapter.validate(pubmed_document)
    # Verify raw is narrowed
    assert is_pubmed_payload(pubmed_document.raw)
```

### Mypy Verification

Run mypy on test files to verify narrowing works:

```bash
mypy --strict tests/ingestion/test_adapters.py
```

Should show that `document.raw["field"]` is allowed after type guard.

## Risks & Mitigations

### Risk: Type Guard False Positives

- **Impact**: Guard matches wrong payload type
- **Mitigation**: Use multiple discriminating fields, not just one
- **Example**: LOINC and SNOMED both have "code", so check additional fields

### Risk: Optional Fields Break Guards

- **Impact**: Guard checks for field that's NotRequired
- **Mitigation**: Only check required fields or fields likely present (>80%)
- **Document**: Which fields are used for discrimination

### Risk: Performance Regression

- **Impact**: Type guard slower than isinstance
- **Mitigation**: Benchmark shows negligible difference (<1μs)
- **Acceptance**: Type safety worth tiny cost

## Success Metrics

- ✅ 5 family-level type guards implemented
- ✅ 8 adapter validate() methods refactored
- ✅ Zero isinstance(document.raw, Mapping) patterns remain
- ✅ Mypy verifies type narrowing works
- ✅ All tests pass unchanged

## Future Work

- Fine-grained adapter-specific guards if needed
- Type guards for IR layer (Proposal 5)
- Generic type guard decorator for payload validation
