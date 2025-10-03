# Follow-up Proposals for refactor-ingestion-typedicts

This document outlines comprehensive follow-up work needed after completing the `refactor-ingestion-typedicts` change.

## Executive Summary

The `refactor-ingestion-typedicts` change introduced adapter-specific TypedDict payloads in `src/Medical_KG/ingestion/types.py`, but substantial integration work remains:

- **5 terminology adapters** (MeSH, UMLS, LOINC, ICD-11, SNOMED) lack Generic[RawPayloadT] parameterization
- **3 literature adapters** (PubMed, PMC, MedRxiv) lack type parameters and have ~50 mypy union-attr errors
- **29 `cast()` calls** remain across ingestion adapters
- **46 `ensure_json_mapping/sequence` calls** indicate runtime validation that should be compile-time
- **Document.raw validation** uses runtime `isinstance()` checks in 8 adapter `validate()` methods
- **No IR integration**: IR builder doesn't consume typed Document.raw
- **Test gaps**: Optional (NotRequired) fields lack systematic coverage

---

## Proposal 1: Complete Adapter Type Parameterization

### Change ID

`complete-ingestion-adapter-type-params`

### Why

5 terminology adapters and 3 literature adapters inherit `HttpAdapter` without specifying `Generic[RawPayloadT]`, causing mypy strict errors and preventing compile-time payload validation.

### What Changes

- Parameterize `MeSHAdapter`, `UMLSAdapter`, `LoincAdapter`, `Icd11Adapter`, `SnomedAdapter` with their respective TypedDict types
- Parameterize `PubMedAdapter`, `PmcAdapter`, `MedRxivAdapter` with literature payload types
- Update `parse()` signatures to accept typed `raw` parameters
- Replace dict literals in `parse()` with proper TypedDict construction

### Affected Files

- `src/Medical_KG/ingestion/adapters/terminology.py` (5 adapters × ~50 lines each)
- `src/Medical_KG/ingestion/adapters/literature.py` (3 adapters × ~150 lines each)
- `tests/ingestion/test_adapters.py` (add/update type assertions)

### Mypy Errors Resolved

- 10 "Missing type parameters for generic type" errors
- 10 "Argument 'raw' to Document has incompatible type" errors
- ~50 "union-attr" errors in literature adapters

### Acceptance Criteria

- All adapters declare `class XAdapter(HttpAdapter[XPayload]):`
- `mypy --strict src/Medical_KG/ingestion/adapters` passes for terminology.py and literature.py
- No new `# type: ignore` comments added

---

## Proposal 2: Eliminate Document.raw Runtime Type Checks

### Change ID

`add-document-raw-type-guards`

### Why

8 adapter `validate()` methods perform `isinstance(document.raw, Mapping)` checks and then index into raw, defeating TypedDict benefits. This creates runtime coupling and prevents static analysis.

### What Changes

- Introduce type guard helper functions in `src/Medical_KG/ingestion/types.py`:
  - `is_terminology_payload(raw: DocumentRaw) -> TypeGuard[TerminologyDocumentPayload]`
  - `is_literature_payload(raw: DocumentRaw) -> TypeGuard[LiteratureDocumentPayload]`
  - `is_clinical_payload(raw: DocumentRaw) -> TypeGuard[ClinicalCatalogDocumentPayload]`
  - etc.
- Refactor adapter `validate()` methods to use type guards for narrowing
- Remove `isinstance(document.raw, Mapping)` runtime checks

### Example Transformation

**Before:**

```python
def validate(self, document: Document) -> None:
    raw = document.raw
    pmid = raw["pmid"] if isinstance(raw, Mapping) else None
    if not isinstance(pmid, (str, int)) or not PMID_RE.match(str(pmid)):
        raise ValueError("Invalid PMID")
```

**After:**

```python
def validate(self, document: Document) -> None:
    raw = document.raw
    assert is_pubmed_payload(raw), "PubMedAdapter produced non-PubMed payload"
    if not PMID_RE.match(str(raw["pmid"])):
        raise ValueError("Invalid PMID")
```

### Affected Files

- `src/Medical_KG/ingestion/types.py` (new type guards, ~80 lines)
- `src/Medical_KG/ingestion/adapters/*.py` (8 validate() methods)
- `tests/ingestion/test_adapters.py` (add type guard tests)

### Acceptance Criteria

- Type guards defined for all 5 payload family unions
- Zero `isinstance(document.raw, Mapping)` patterns in adapter code
- `validate()` methods leverage static typing via guards

---

## Proposal 3: Reduce Runtime Validation Helpers

### Change ID

`reduce-ingestion-runtime-validation`

### Why

46 calls to `ensure_json_mapping()` and `ensure_json_sequence()` indicate weak upstream typing. With typed adapters, many become redundant.

### What Changes

- Audit all `ensure_json_mapping/sequence` calls in `adapters/clinical.py` (32 calls), `adapters/guidelines.py` (12 calls), `adapters/literature.py` (2 calls)
- Remove calls where upstream TypedDict already guarantees structure
- Keep calls only at HTTP API boundaries where external JSON is first parsed
- Document remaining usage in module docstrings as "external boundary validation"

### Metrics

- **Current**: 46 `ensure_*` calls
- **Target**: ≤15 calls (only at `fetch_json()` return sites)

### Affected Files

- `src/Medical_KG/ingestion/adapters/clinical.py` (reduce 32→8)
- `src/Medical_KG/ingestion/adapters/guidelines.py` (reduce 12→4)
- `src/Medical_KG/ingestion/utils.py` (add deprecation notice if usage drops)

### Risks

- Removing validation prematurely if upstream API changes format
- **Mitigation**: Keep validation at fetch boundaries, document API version dependencies

---

## Proposal 4: Eliminate typing.cast in Adapters

### Change ID

`eliminate-ingestion-adapter-casts`

### Why

29 `cast()` calls across ingestion adapters indicate type system workarounds. Proper TypedDict usage should eliminate most.

### What Changes

- Replace `cast(JSONValue, raw.get(...))` with TypedDict-aware access patterns
- Introduce narrowing helper functions for JSONValue→JSONMapping/JSONSequence
- Update `ClinicalTrialsGovAdapter.parse()` (20 casts) to use typed intermediate variables
- Update `OpenFdaAdapter` (cast at line 272) to return properly typed records from fetch()

### Cast Breakdown (by file)

- `utils.py`: 2 (ensure_* helpers, keep for boundary validation)
- `clinical.py`: 20 (mostly ClinicalTrialsGovAdapter.parse)
- `guidelines.py`: 3
- `ledger.py`: 3
- `http_client.py`: 1

### Target Reduction

- **Current**: 29 casts
- **Target**: ≤5 casts (only at external API parsing boundaries)

### Affected Files

- `src/Medical_KG/ingestion/adapters/clinical.py`
- `src/Medical_KG/ingestion/adapters/guidelines.py`
- `src/Medical_KG/ingestion/types.py` (new narrowing helpers)

---

## Proposal 5: Integrate Typed Payloads with IR Layer

### Change ID

`integrate-document-raw-with-ir`

### Why

`IrBuilder` accepts generic `metadata: Mapping[str, Any]` and doesn't leverage typed `Document.raw`. Downstream IR validation can't benefit from compile-time guarantees.

### What Changes

- Extend `IrBuilder.build()` to optionally accept `raw: AdapterDocumentPayload | None`
- Create IR-specific payload extractors:
  - Extract provenance metadata from literature payloads (PMC sections, PubMed MeSH terms)
  - Extract structured blocks from clinical payloads (trial arms, outcomes)
- Update `ir/validator.py` to perform payload-aware validation
- Add integration tests for Document→IR transformation with typed payloads

### Affected Files

- `src/Medical_KG/ir/builder.py` (~30 new lines)
- `src/Medical_KG/ir/validator.py` (~20 new lines)
- `src/Medical_KG/ir/models.py` (optional: add `source_payload` field to DocumentIR)
- `tests/ir/test_builder.py` (new payload integration tests)

### Benefits

- IR can extract structured metadata without parsing JSON strings
- Type-safe bridge between ingestion and IR layers
- Foundation for source-specific IR enrichment

---

## Proposal 6: Comprehensive Test Coverage for Optional Fields

### Change ID

`test-ingestion-optional-fields`

### Why

All adapter payloads use `NotRequired` for optional fields, but tests don't systematically verify behavior when fields are present/absent.

### What Changes

- For each adapter payload with ≥1 NotRequired field:
  - Add test case with all optional fields present
  - Add test case with all optional fields absent
  - Add test case with mixed presence (realistic scenario)
- Ensure validation logic handles `None` vs absent key correctly
- Test that `Document.content` and `metadata` are stable regardless of optional field presence

### Coverage Targets (by adapter family)

- **Terminology** (6 adapters, avg 3 optional fields each): 18 test cases
- **Clinical** (3 adapters, avg 8 optional fields each): 24 test cases
- **Literature** (3 adapters, avg 4 optional fields each): 12 test cases
- **Guidelines** (2 adapters, avg 2 optional fields each): 6 test cases
- **Knowledge** (4 adapters, avg 2 optional fields each): 8 test cases

**Total new test cases**: ~68

### Affected Files

- `tests/ingestion/fixtures/*.py` (add optional-field fixtures)
- `tests/ingestion/test_adapters.py` (parametrized tests per adapter)
- `tests/ingestion/test_optional_fields.py` (new module)

### Acceptance Criteria

- Every `NotRequired` field appears in ≥2 test scenarios (present + absent)
- Test suite documents which optional fields are "commonly present" vs "rarely present"

---

## Proposal 7: Update Ingestion Developer Documentation

### Change ID

`document-ingestion-typed-payloads`

### Why

New contributors must understand:

- How to define adapter-specific TypedDicts
- When to use `NotRequired` vs required fields
- How to write type-safe `parse()` implementations
- How typed payloads flow to IR and downstream consumers

### What Changes

- Create `docs/ingestion_typed_contracts.md`:
  - Adapter TypedDict design patterns
  - Mixin usage guide (IdentifierMixin, VersionMixin, etc.)
  - NotRequired field conventions
  - Type guard usage examples
- Update `docs/ingestion_runbooks.md`:
  - Add "Adding a New Adapter" section with typed payload scaffolding
  - Migration guide from `Any`-typed to TypedDict adapters
- Update `CONTRIBUTING.md`:
  - Require TypedDict definitions for new adapters
  - Mypy strict compliance checklist
- Add module docstrings to `src/Medical_KG/ingestion/types.py`:
  - Document each payload family union
  - Explain mixin inheritance patterns

### Affected Files

- `docs/ingestion_typed_contracts.md` (new, ~300 lines)
- `docs/ingestion_runbooks.md` (update, +150 lines)
- `CONTRIBUTING.md` (update, +50 lines)
- `src/Medical_KG/ingestion/types.py` (add docstrings, +100 lines)

### Acceptance Criteria

- Developer can create new typed adapter in <2 hours following docs
- Documentation includes 3 complete examples (terminology, literature, clinical)
- CI checks enforce TypedDict usage for adapter PRs

---

## Implementation Sequencing

### Phase 1: Foundation (Proposals 1 & 2)

**Duration**: 5-7 days

- Complete adapter type parameterization
- Add type guards for Document.raw
- **Blocker for**: All other proposals depend on typed adapters

### Phase 2: Type System Cleanup (Proposals 3 & 4)

**Duration**: 4-6 days

- Reduce runtime validation helpers
- Eliminate casts
- **Depends on**: Phase 1

### Phase 3: Integration & Testing (Proposals 5 & 6)

**Duration**: 6-8 days

- IR layer integration
- Comprehensive optional field tests
- **Depends on**: Phases 1 & 2

### Phase 4: Documentation (Proposal 7)

**Duration**: 3-4 days

- Can start in parallel with Phase 2
- Final review after Phase 3 completes

**Total estimated duration**: 18-25 days (assuming 1 FTE)

---

## Coordination with Active Changes

### Must Coordinate With

- **update-type-safety-ingestion-base**: Overlaps on adapter type annotations
- **update-type-safety-ingestion-catalog**: IR integration may conflict
- **add-ingestion-test-coverage**: Test infrastructure dependencies
- **add-test-infrastructure-ci-enforcement**: Mypy strict CI gates

### Suggested Approach

1. Freeze `update-type-safety-ingestion-base` and `update-type-safety-ingestion-catalog` tasks
2. Complete Proposals 1-4 (foundation + cleanup)
3. Merge and rebase type-safety changes against new baseline
4. Continue with Proposals 5-7

---

## Success Metrics

### Static Analysis

- `mypy --strict src/Medical_KG/ingestion` passes with 0 errors (currently ~120 errors)
- Zero new `# type: ignore` comments in ingestion module
- `cast()` usage reduced by ≥80% (29→≤5)

### Code Quality

- `ensure_json_*` calls reduced by ≥67% (46→≤15)
- All 18 adapters parameterize Generic[RawPayloadT]
- Type guard functions cover all 5 payload family unions

### Test Coverage

- ≥68 new test cases for optional field scenarios
- All `NotRequired` fields tested in present + absent states
- Integration tests verify Document.raw→DocumentIR flow

### Documentation

- Developer onboarding guide includes 3 complete typed adapter examples
- CONTRIBUTING.md mandates TypedDict for new adapters
- CI rejects PRs with untyped adapter additions

---

## Risk Assessment

### High Risk

- **Parallel type-safety changes** may cause merge conflicts
  - **Mitigation**: Coordinate freeze windows, rebase frequently
- **Runtime regressions** from removing validation
  - **Mitigation**: Chaos tests, integration test suite, staged rollout

### Medium Risk

- **Developer adoption** of type guards and mixins
  - **Mitigation**: Comprehensive docs, PR review checklists
- **IR integration** breaking existing workflows
  - **Mitigation**: IR changes optional/backward-compatible initially

### Low Risk

- **Test suite expansion** increasing CI time
  - **Mitigation**: Parametrize tests, run optional-field tests in separate job

---

## Appendix: Current State Analysis

### Adapter Type Parameter Status

| Adapter Family | Adapters | Typed | Untyped |
|---------------|----------|-------|---------|
| Terminology | 6 | 1 (AccessGudid) | 5 (MeSH, UMLS, LOINC, ICD-11, SNOMED) |
| Literature | 3 | 0 | 3 (PubMed, PMC, MedRxiv) |
| Clinical | 5 | 3 (ClinicalTrials, OpenFDA, RxNorm) | 2 (DailyMed, AccessGudid†) |
| Guidelines | 6 | 6 (all) | 0 |
| Knowledge | 4 | 4 (all) | 0 |

**Total**: 24 adapters, 14 typed (58%), 10 untyped (42%)

†AccessGudid listed in both clinical and terminology based on implementation

### Mypy Strict Error Distribution

```
terminology.py:  11 errors (type-arg: 5, arg-type: 5, union-attr: 1)
literature.py:   ~108 errors (union-attr: ~100, arg-type: 8)
clinical.py:     ~15 errors (union-attr, arg-type)
guidelines.py:   ~5 errors
```

**Total ingestion adapter errors**: ~139

### Document.raw Validation Patterns

8 adapters access `document.raw` in `validate()` methods:

- 3 literature adapters: runtime `isinstance(raw, Mapping)` checks
- 1 terminology adapter: `document.raw.get()` without guard (line 246)
- 1 clinical adapter: `isinstance(document.raw, Mapping)` check (line 225)

All indicate need for type guards.

---

## Questions for Review

1. **Scope**: Should Proposal 5 (IR integration) be deferred to a separate epic given its cross-cutting nature?
2. **Priority**: Is eliminating casts (Proposal 4) more urgent than test coverage (Proposal 6)?
3. **Coordination**: Should we block on freezing `update-type-safety-ingestion-*` or proceed in parallel?
4. **Metrics**: Are the success metrics (0 mypy errors, 80% cast reduction) achievable or should we target incremental milestones?

---

**Document Version**: 1.0
**Author**: AI Assistant (Codex)
**Date**: 2025-10-03
**Status**: Draft for Review
