# Follow-up Work Summary for refactor-ingestion-typedicts

## Quick Stats

- **7 comprehensive follow-up proposals** identified
- **Estimated effort**: 18-25 days (1 FTE)
- **Current mypy errors**: ~139 in ingestion adapters
- **Target**: 0 errors, full `mypy --strict` compliance

## The 7 Proposals

### 1. Complete Adapter Type Parameterization

**Effort**: 3-4 days | **Priority**: Critical | **ID**: `complete-ingestion-adapter-type-params`

Fix 10 untyped adapters (5 terminology, 3 literature, 2 clinical) that lack `Generic[RawPayloadT]` specification. Resolves ~70 mypy errors.

### 2. Add Document.raw Type Guards

**Effort**: 2-3 days | **Priority**: High | **ID**: `add-document-raw-type-guards`

Replace runtime `isinstance(document.raw, Mapping)` checks in 8 adapter `validate()` methods with compile-time type guards.

### 3. Reduce Runtime Validation Helpers

**Effort**: 2-3 days | **Priority**: Medium | **ID**: `reduce-ingestion-runtime-validation`

Reduce 46 `ensure_json_mapping/sequence()` calls to ≤15 by leveraging TypedDict guarantees.

### 4. Eliminate typing.cast in Adapters

**Effort**: 2-3 days | **Priority**: Medium | **ID**: `eliminate-ingestion-adapter-casts`

Remove 29 `cast()` calls (target: ≤5) by improving TypedDict construction patterns, especially in `ClinicalTrialsGovAdapter`.

### 5. Integrate Typed Payloads with IR Layer

**Effort**: 3-4 days | **Priority**: Medium | **ID**: `integrate-document-raw-with-ir`

Extend `IrBuilder` to consume typed `Document.raw`, enabling structured metadata extraction and type-safe IR construction.

### 6. Comprehensive Test Coverage for Optional Fields

**Effort**: 4-6 days | **Priority**: High | **ID**: `test-ingestion-optional-fields`

Add ~68 test cases covering all `NotRequired` field combinations across 18 adapters (present/absent/mixed scenarios).

### 7. Update Ingestion Developer Documentation

**Effort**: 3-4 days | **Priority**: Low | **ID**: `document-ingestion-typed-payloads`

Create `docs/ingestion_typed_contracts.md` (~300 lines) with adapter TypedDict patterns, mixin usage, and migration guides.

---

## Recommended Implementation Sequence

### Phase 1: Foundation (Weeks 1-2)

- ✅ **Proposal 1**: Complete adapter parameterization
- ✅ **Proposal 2**: Add type guards

*Blockers removed for all downstream work*

### Phase 2: Cleanup (Week 2-3)

- ✅ **Proposal 3**: Reduce runtime validation
- ✅ **Proposal 4**: Eliminate casts

*mypy --strict compliance achieved*

### Phase 3: Integration (Week 3-4)

- ✅ **Proposal 5**: IR integration
- ✅ **Proposal 6**: Test coverage

*Full end-to-end type safety*

### Phase 4: Documentation (Week 4)

- ✅ **Proposal 7**: Developer docs (parallel with Phase 2)

---

## Key Coordination Points

### Must Sync With

- `update-type-safety-ingestion-base` (11 tasks open)
- `update-type-safety-ingestion-catalog` (8 tasks open)
- `add-ingestion-test-coverage` (complete, but fixtures may need updates)

### Suggested Approach

1. Freeze related type-safety changes
2. Complete Proposals 1-4 (foundation)
3. Rebase type-safety changes against new baseline
4. Continue with Proposals 5-7

---

## Success Metrics

| Metric | Current | Target | Improvement |
|--------|---------|--------|-------------|
| Mypy errors (ingestion adapters) | ~139 | 0 | 100% |
| Typed adapters | 14/24 (58%) | 24/24 (100%) | +10 adapters |
| `cast()` calls | 29 | ≤5 | -83% |
| `ensure_json_*` calls | 46 | ≤15 | -67% |
| Test cases for NotRequired fields | 0 | 68 | +68 |

---

## Next Steps

1. **Review** REFACTOR_FOLLOWUP_PROPOSALS.md for detailed specifications
2. **Decide** on coordination strategy with `update-type-safety-*` changes
3. **Approve** proposals for OpenSpec scaffolding
4. **Prioritize** if all 7 proposals or subset should proceed

---

## Questions to Resolve

- Should Proposal 5 (IR integration) be deferred to separate epic?
- Proceed in parallel with `update-type-safety-*` or freeze first?
- Target all 7 proposals or focus on Proposals 1-4 (foundation) initially?
- Are success metrics (0 errors, 80% cast reduction) achievable?

**Ready for**: Proposal review → OpenSpec scaffolding → Implementation
