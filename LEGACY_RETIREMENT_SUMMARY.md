# Legacy Debt Retirement - Quick Reference

## Overview

Six OpenSpec proposals systematically remove all legacy compatibility layers from the Medical_KG codebase after successful completion of streaming pipeline, state machine, TypedDict, CLI unification, and telemetry refactorings.

## What Was Created

### ✅ Proposal 1: remove-run-async-legacy (VALIDATED)

**Purpose**: Delete deprecated `run_async_legacy()` pipeline wrapper after >95% streaming API adoption

**Impact**: -200 lines of deprecated code, cleaner pipeline implementation

**Tasks**: 70 | **Duration**: 3-4 days | **Risk**: 🔴 High (breaking)

---

### ✅ Proposal 2: purge-legacy-ledger-compat (VALIDATED)

**Purpose**: Remove `LedgerState.LEGACY` enum value and string coercion after full enum migration

**Impact**: -200 lines of compatibility code, O(1) ledger initialization

**Tasks**: 105 | **Duration**: 4-5 days | **Risk**: 🔴 High (requires compaction)

---

### ✅ Proposal 3: retire-ir-legacy-fallbacks (VALIDATED)

**Purpose**: Require typed `Document.raw` payloads in IR builder, remove fallback coercion

**Impact**: -80 lines of defensive code, type-safe Document→IR flow

**Tasks**: 98 | **Duration**: 3 days | **Risk**: 🟡 Medium

---

### ✅ Proposal 4: remove-legacy-ingestion-tooling (VALIDATED)

**Purpose**: Delete CLI migration scripts and tooling after unification complete

**Impact**: -500 lines of migration-only code, clearer documentation

**Tasks**: 98 | **Duration**: 2 days | **Risk**: 🟢 Low (tooling only)

---

### ✅ Proposal 5: normalize-http-telemetry (VALIDATED)

**Purpose**: Remove `_NoopMetric` placeholders, centralize telemetry through registry

**Impact**: -50 lines of placeholder code, explicit metrics configuration

**Tasks**: 105 | **Duration**: 5 days | **Risk**: 🟡 Minor (config change)

---

### ✅ Proposal 6: clean-legacy-test-surfaces (VALIDATED)

**Purpose**: Delete tests for removed APIs and legacy fixtures, add current API smoke tests

**Impact**: -260 lines of obsolete tests, faster CI execution

**Tasks**: 105 | **Duration**: 3 days | **Risk**: 🟢 Low (test-only)

---

## Quick Stats

| Metric | Value |
|--------|-------|
| **Total Proposals** | 6 |
| **Total Tasks** | 581 |
| **Code Removed** | ~1,290 lines |
| **Duration** | 6 weeks (1 FTE) |
| **All Validated** | ✅ YES |

---

## Implementation Sequence

```
Week 1-2: Foundation (Proposals 1, 4)
Week 3-4: Core Infrastructure (Proposals 2, 3 in parallel)
Week 5:   Telemetry Normalization (Proposal 5)
Week 6:   Test Cleanup (Proposal 6)
```

---

## Key Dependencies

1. **Proposal 1** → `refactor-ingestion-pipeline-streaming` deployed
2. **Proposal 2** → `refactor-ledger-state-machine` implemented
3. **Proposal 3** → All 7 TypedDict proposals completed
4. **Proposal 4** → CLI unification Phase 3 (>95% adoption)
5. **Proposal 5** → `add-http-client-telemetry` foundation
6. **Proposal 6** → Proposals 1-5 completed

---

## Validation Commands

```bash
# Validate all proposals
for p in remove-run-async-legacy purge-legacy-ledger-compat \
         retire-ir-legacy-fallbacks remove-legacy-ingestion-tooling \
         normalize-http-telemetry clean-legacy-test-surfaces; do
  openspec validate $p --strict
done

# View specific proposal
openspec show remove-run-async-legacy

# List all proposals
openspec list | grep -E "(remove-run|purge-legacy|retire-ir|remove-legacy-ingestion|normalize-http|clean-legacy)"
```

---

## Expected Benefits

### Code Quality

- 1,290 lines of legacy code removed
- 100% type-safe operations (enum states, typed payloads)
- Single canonical API surface

### Performance

- O(1) ledger initialization (no string translation)
- Faster test suite execution
- Reduced telemetry overhead

### Developer Experience

- Clearer documentation (current API only)
- No deprecated method confusion
- Easier onboarding for new contributors

---

## Files Created

```
openspec/changes/
├── remove-run-async-legacy/          (3 files, 70 tasks)
├── purge-legacy-ledger-compat/       (3 files, 105 tasks)
├── retire-ir-legacy-fallbacks/       (3 files, 98 tasks)
├── remove-legacy-ingestion-tooling/  (3 files, 98 tasks)
├── normalize-http-telemetry/         (3 files, 105 tasks)
└── clean-legacy-test-surfaces/       (3 files, 105 tasks)

Documentation/
├── LEGACY_RETIREMENT_COMPLETE.md     (Comprehensive guide)
└── LEGACY_RETIREMENT_SUMMARY.md      (This file - Quick reference)
```

---

## Related Documentation

- **Source Requirements**: `openspec/changes/LEGACY_RETIREMENT_SCOPES.md`
- **Recent Refactorings**:
  - `openspec/changes/TYPED_PAYLOADS_COMPLETE.md`
  - `openspec/changes/REFACTOR_FOLLOWUP_PROPOSALS.md`
  - `REPOSITORY_OPTIMIZATION_COMPLETE.md`
  - `CLI_UNIFICATION_ROADMAP.md`

---

## Status

**✅ ALL PROPOSALS CREATED AND VALIDATED**

Ready for:

- Stakeholder review
- Resource allocation
- Implementation kickoff

---

**Created**: 2025-10-04
**Version**: 1.0
**Status**: Ready for Review
