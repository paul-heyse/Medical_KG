# Implementation Plan: refactor-ingestion-typedicts Follow-up Work

This document provides a comprehensive implementation plan for the 7 follow-up proposals stemming from the `refactor-ingestion-typedicts` change.

## Executive Summary

- **7 proposals** addressing complete TypedDict integration
- **Estimated effort**: 18-25 days (1 FTE)
- **Current state**: Types defined, 14/24 adapters typed, ~139 mypy errors
- **Target state**: 24/24 adapters typed, 0 mypy errors, full type safety

## Proposal Status

| # | Proposal ID | Priority | Status | Tasks | Est. Days |
|---|------------|----------|--------|-------|-----------|
| 1 | complete-ingestion-adapter-type-params | Critical | ✅ Ready | 0/48 | 3-4 |
| 2 | add-document-raw-type-guards | High | ✅ Ready | 0/17 | 2-3 |
| 3 | reduce-ingestion-runtime-validation | Medium | ✅ Ready | 0/17 | 2-3 |
| 4 | eliminate-ingestion-adapter-casts | Medium | ✅ Ready | 0/16 | 2-3 |
| 5 | integrate-document-raw-with-ir | Medium | ✅ Ready | 0/22 | 3-4 |
| 6 | test-ingestion-optional-fields | High | ✅ Ready | 0/21 | 4-6 |
| 7 | document-ingestion-typed-payloads | Low | ✅ Ready | 0/28 | 3-4 |

**All proposals validated with `openspec validate --strict` ✓**

## Implementation Phases

### Phase 1: Foundation (Week 1-2) - CRITICAL PATH

**Proposals**: 1 (type params) + 2 (type guards)
**Duration**: 5-7 days
**Blockers**: None
**Blocked**: All other proposals depend on this

#### Dependencies

```
refactor-ingestion-typedicts (complete)
    ↓
Proposal 1: complete-ingestion-adapter-type-params (3-4 days)
    ↓
Proposal 2: add-document-raw-type-guards (2-3 days)
```

#### Deliverables

- ✅ 8 untyped adapters (5 terminology, 3 literature) fully parameterized
- ✅ ~70 mypy errors resolved
- ✅ Type guard functions for all 5 payload families
- ✅ 8 adapter validate() methods using type guards
- ✅ Zero isinstance(document.raw, Mapping) patterns

#### Success Criteria

```bash
mypy --strict src/Medical_KG/ingestion/adapters/terminology.py  # 0 errors
mypy --strict src/Medical_KG/ingestion/adapters/literature.py   # 0 errors
pytest tests/ingestion/ -v                                       # all pass
```

#### Coordination

- **Must freeze**: `update-type-safety-ingestion-base` (11 tasks, overlapping scope)
- **Notify**: `update-type-safety-ingestion-catalog` team (may need rebase)

---

### Phase 2: Type System Cleanup (Week 2-3)

**Proposals**: 3 (validation) + 4 (casts)
**Duration**: 4-6 days
**Depends on**: Phase 1 complete
**Blocked**: None after Phase 1

#### Dependencies

```
Phase 1 (complete)
    ↓
Proposal 3: reduce-ingestion-runtime-validation (2-3 days)
    ↓ (parallel possible)
Proposal 4: eliminate-ingestion-adapter-casts (2-3 days)
```

#### Deliverables

- ✅ `ensure_json_*` calls reduced 46→≤15 (67% reduction)
- ✅ `cast()` calls reduced 29→≤5 (83% reduction)
- ✅ Narrowing helper functions added to types.py
- ✅ Boundary validation documented

#### Success Criteria

```bash
grep -r "ensure_json_mapping\|ensure_json_sequence" src/Medical_KG/ingestion/ | wc -l  # ≤15
grep -r "cast(" src/Medical_KG/ingestion/ | wc -l                                      # ≤5
mypy --strict src/Medical_KG/ingestion                                                  # 0 errors
```

#### Coordination

- **Sync with**: `add-ingestion-test-coverage` (complete, but fixtures may need updates)

---

### Phase 3: Integration & Testing (Week 3-4)

**Proposals**: 5 (IR integration) + 6 (test coverage)
**Duration**: 6-8 days
**Depends on**: Phases 1-2 complete
**Blocked**: None after Phase 2

#### Dependencies

```
Phase 1 + Phase 2 (complete)
    ↓
Proposal 5: integrate-document-raw-with-ir (3-4 days)
    ↓ (parallel possible)
Proposal 6: test-ingestion-optional-fields (4-6 days)
```

#### Deliverables

- ✅ IrBuilder accepts AdapterDocumentPayload parameter
- ✅ Payload extractors for literature/clinical/guidelines
- ✅ ~68 new test cases for NotRequired field scenarios
- ✅ Integration tests for Document→DocumentIR flow

#### Success Criteria

```bash
pytest tests/ir/test_builder.py -v              # all pass with typed payloads
pytest tests/ingestion/test_optional_fields.py  # ≥68 tests, all pass
coverage report --include="src/Medical_KG/ingestion/*"  # NotRequired fields tested
```

#### Coordination

- **Sync with**: `update-type-safety-core-services` (IR validation overlap)

---

### Phase 4: Documentation (Week 4) - PARALLEL

**Proposals**: 7 (documentation)
**Duration**: 3-4 days
**Depends on**: Can start in parallel with Phase 2
**Blocked**: Final review after Phase 3

#### Dependencies

```
Phase 1 (for examples)
    ↓
Proposal 7: document-ingestion-typed-payloads (3-4 days)
    ↓
Final review after Phase 3 (1 day)
```

#### Deliverables

- ✅ `docs/ingestion_typed_contracts.md` (~300 lines)
- ✅ `docs/ingestion_runbooks.md` updated (+150 lines)
- ✅ `CONTRIBUTING.md` updated (+50 lines)
- ✅ Module docstrings in `ingestion/types.py` (+100 lines)

#### Success Criteria

- Developer can create typed adapter in <2 hours following docs
- Documentation includes 3 complete examples (terminology, literature, clinical)
- CI enforcement checklist in CONTRIBUTING.md

---

## Resource Allocation

### Single FTE Path (Conservative: 25 days)

```
Week 1: Phase 1 (5 days) + buffer (2 days)
Week 2: Phase 2 (5 days) + documentation start (2 days)
Week 3: Phase 3 part 1 (IR integration, 4 days) + doc work (1 day)
Week 4: Phase 3 part 2 (test coverage, 5 days)
Week 5: Documentation finalization + review (4 days) + buffer (1 day)
```

### 2 FTE Path (Optimistic: 13 days)

```
Week 1: FTE1: Phase 1 (5 days), FTE2: Documentation (5 days)
Week 2: FTE1: Phase 2 (5 days), FTE2: Phase 3 test coverage (5 days)
Week 3: FTE1: Phase 3 IR integration (3 days), FTE2: Finalize docs (3 days)
```

## Coordination Strategy

### Active Change Freeze Windows

**Option A: Sequential (Safer)**

1. Freeze `update-type-safety-ingestion-base` and `update-type-safety-ingestion-catalog`
2. Complete Phases 1-2 (foundation + cleanup)
3. Merge frozen changes against new baseline
4. Continue with Phases 3-4

**Option B: Parallel (Riskier, Faster)**

1. Coordinate daily standups with type-safety teams
2. Implement changes in separate branches
3. Use frequent rebasing to catch conflicts early
4. Merge in sequence: Phase 1 → type-safety → Phase 2-4

**Recommendation**: Option A for Phases 1-2, then Option B for Phases 3-4

### Communication Plan

**Daily Updates** (during Phases 1-2):

- Mypy error count
- Tasks completed
- Blockers encountered

**Weekly Reviews**:

- Phase completion demos
- Coordination with type-safety teams
- Adjust timeline if needed

**Milestone Announcements**:

- Phase 1 complete: "All adapters typed, ready for cleanup"
- Phase 2 complete: "mypy --strict passes, type system clean"
- Phase 3 complete: "Full integration + test coverage"
- Phase 4 complete: "Documentation ready for new contributors"

## Risk Management

### High-Risk Items

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Merge conflicts with parallel work | High | 70% | Freeze windows, frequent rebasing |
| Union-attr errors proliferate beyond 50 | Medium | 40% | Systematic narrowing, escalate if >100 |
| Test fixtures need extensive updates | Medium | 60% | Audit fixtures in Phase 1, update early |
| Runtime regressions from type changes | Medium | 30% | Chaos tests, staged rollout |

### Mitigation Actions

**For merge conflicts**:

- Establish freeze window for Phases 1-2
- Create `type-refactor` integration branch
- Daily sync meetings with affected teams

**For error proliferation**:

- Track error count daily
- Define escalation threshold (>100 errors)
- Have JSONValue redesign proposal ready if needed

**For test regressions**:

- Run full test suite after each adapter
- Keep old implementation in git history for quick rollback
- Use feature flags if runtime changes needed

## Acceptance Criteria (Overall)

### Static Analysis

- [ ] `mypy --strict src/Medical_KG/ingestion` passes with 0 errors
- [ ] Zero new `# type: ignore` comments added
- [ ] All 24 adapters declare `Generic[RawPayloadT]`

### Code Quality

- [ ] `cast()` usage: 29 → ≤5 (83% reduction)
- [ ] `ensure_json_*` calls: 46 → ≤15 (67% reduction)
- [ ] Type guard functions cover all 5 payload families
- [ ] Zero `isinstance(document.raw, Mapping)` patterns

### Test Coverage

- [ ] ≥68 new test cases for NotRequired fields
- [ ] All optional fields tested in present + absent states
- [ ] Integration tests for Document→DocumentIR flow
- [ ] All existing tests pass unchanged

### Documentation

- [ ] `docs/ingestion_typed_contracts.md` created (~300 lines)
- [ ] 3 complete adapter examples (terminology, literature, clinical)
- [ ] CONTRIBUTING.md mandates TypedDict for new adapters
- [ ] CI enforces typed adapters for new PRs

## Rollout Plan

### Staging Deployment

1. Deploy Phase 1 changes to staging
2. Run ingestion smoke tests
3. Monitor error logs for 24 hours
4. Verify type checking in CI

### Production Deployment

1. Deploy during low-traffic window
2. Enable monitoring alerts for ingestion failures
3. Keep Phase 0 (pre-refactor) branch available for quick rollback
4. Monitor for 48 hours before marking complete

### Rollback Criteria

- Ingestion failure rate increases >5%
- Mypy CI blocks legitimate PRs
- Test suite time increases >20%
- Developer complaints about type friction

## Success Metrics Dashboard

Track these metrics throughout implementation:

```python
# Static Analysis
mypy_errors = {
    "terminology.py": 11 → 0,
    "literature.py": 108 → 0,
    "clinical.py": 15 → 0,
    "total": 139 → 0
}

# Code Quality
cast_count = 29 → 5  # 83% reduction
ensure_json_count = 46 → 15  # 67% reduction
typed_adapters = 14 → 24  # 100% coverage

# Test Coverage
optional_field_tests = 0 → 68
integration_tests = baseline → baseline + 12

# Developer Experience
time_to_create_adapter = "unknown" → "<2 hours"
contributor_questions = baseline → -50%  # after docs
```

## Post-Deployment

### Monitoring (First Week)

- Track ingestion success rate
- Monitor CI build times
- Collect developer feedback
- Review PR velocity impact

### Retrospective (After 2 Weeks)

- What went well?
- What took longer than expected?
- What would we do differently?
- Document lessons for future type safety work

### Continuous Improvement

- Update documentation based on feedback
- Add more type guard examples if needed
- Refine CI checks for optimal balance
- Plan next phase of type safety work

---

## Quick Reference

### Key Commands

```bash
# Validation
openspec validate <proposal-id> --strict

# Type checking
mypy --strict src/Medical_KG/ingestion/adapters/

# Test execution
pytest tests/ingestion/ -v
pytest tests/ir/ -v -k "payload"

# Metrics
grep -r "cast(" src/Medical_KG/ingestion/ | wc -l
grep -r "ensure_json_" src/Medical_KG/ingestion/ | wc -l
```

### Proposal Dependencies

```
1 (type params) → 2 (type guards) → 3 (validation) → 5 (IR integration)
                                   → 4 (casts) ----→ 6 (test coverage)
                  → 7 (docs) ← Phase 1-3 examples
```

### Contact Information

- **Type Safety Lead**: [Coordinate freeze windows]
- **IR Team Lead**: [Proposal 5 integration]
- **QA Lead**: [Test coverage strategy]
- **DevOps**: [CI integration, monitoring]

---

**Document Version**: 1.0
**Created**: 2025-10-03
**Status**: Ready for Implementation
**Next Review**: After Phase 1 completion
