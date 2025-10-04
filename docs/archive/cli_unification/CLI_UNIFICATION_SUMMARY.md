# ARCHIVED: CLI Unification Initiative - Summary

_Archived 2025-10-04 – Retained for historical context._

## Overview

Three OpenSpec change proposals have been created to unify the Medical_KG ingestion CLIs through a phased, low-risk approach.

## What Was Created

### ✅ Proposal 1: extract-ingestion-cli-shared-helpers

**Status**: Validated with `openspec validate --strict`

**Purpose**: Foundation phase - extract common functionality into shared helpers

**Files Created**:

- `openspec/changes/extract-ingestion-cli-shared-helpers/proposal.md`
- `openspec/changes/extract-ingestion-cli-shared-helpers/tasks.md` (88 tasks)
- `openspec/changes/extract-ingestion-cli-shared-helpers/specs/ingestion/spec.md`

**Key Deliverables**:

- New `src/Medical_KG/ingestion/cli_helpers.py` module (~300 lines)
- Refactor both existing CLIs to use shared helpers
- Comprehensive test coverage
- Non-breaking changes

**Duration**: 2-3 weeks

**Risk**: 🟢 Low

---

### ✅ Proposal 2: implement-unified-ingestion-cli

**Status**: Validated with `openspec validate --strict`

**Purpose**: Create single unified CLI with deprecation path for legacy

**Files Created**:

- `openspec/changes/implement-unified-ingestion-cli/proposal.md`
- `openspec/changes/implement-unified-ingestion-cli/tasks.md` (106 tasks)
- `openspec/changes/implement-unified-ingestion-cli/design.md` (comprehensive technical decisions)
- `openspec/changes/implement-unified-ingestion-cli/specs/ingestion/spec.md`

**Key Deliverables**:

- Unified CLI: `med ingest <adapter> [options]`
- Feature parity with both legacy and modern CLIs
- Deprecation delegates with warnings
- Rich progress bars and enhanced UX
- Migration guide and tooling

**Duration**: 3-5 weeks + 3-month migration period

**Risk**: 🟡 Medium

---

### ✅ Proposal 3: remove-legacy-ingestion-cli

**Status**: Validated with `openspec validate --strict`

**Purpose**: Clean up deprecated code after successful migration

**Files Created**:

- `openspec/changes/remove-legacy-ingestion-cli/proposal.md`
- `openspec/changes/remove-legacy-ingestion-cli/tasks.md` (93 tasks)
- `openspec/changes/remove-legacy-ingestion-cli/specs/ingestion/spec.md`

**Key Deliverables**:

- Remove ~500 lines of deprecated code
- Simplify test suite
- Major version bump (2.0.0)
- Clean documentation

**Duration**: 1-2 weeks

**Risk**: 🔴 High for unmigrated users, 🟢 Low for migrated users

**Prerequisites**: >95% adoption, 3+ months post-Phase 2

---

## Additional Documentation

### CLI_UNIFICATION_ROADMAP.md

Comprehensive 40-page implementation guide including:

- Executive summary
- Detailed phase breakdown
- Timeline and dependencies
- Risk management
- Communication plan
- Success metrics
- FAQ and troubleshooting

---

## Quick Reference

### Validation Commands

```bash
# Validate all proposals
openspec validate extract-ingestion-cli-shared-helpers --strict
openspec validate implement-unified-ingestion-cli --strict
openspec validate remove-legacy-ingestion-cli --strict
```

### View Proposals

```bash
# List CLI unification proposals
openspec list | grep -E "(extract-ingestion|implement-unified|remove-legacy)"

# Show specific proposal
openspec show extract-ingestion-cli-shared-helpers
```

### Task Counts

- **Phase 1**: 88 tasks (shared helpers)
- **Phase 2**: 106 tasks (unified CLI)
- **Phase 3**: 93 tasks (legacy removal)
- **Total**: 287 tasks across 3 proposals

---

## Implementation Sequence

```
Phase 1: extract-ingestion-cli-shared-helpers (Weeks 1-3)
    ↓ (depends on completion)
Phase 2: implement-unified-ingestion-cli (Weeks 4-8 + 12-week migration)
    ↓ (requires >95% adoption + 3 months)
Phase 3: remove-legacy-ingestion-cli (Weeks 21-22)
```

**Critical**: Must be executed sequentially. No parallel execution.

---

## Key Decisions

### Technology Choices

1. **Typer** for unified CLI (modern, type-safe, maintainable)
2. **Rich** for progress bars and enhanced terminal output
3. **Soft deprecation** with 3-month migration period
4. **Major version bump** for final breaking change

### Command Structure

**Before (Legacy)**:

```bash
med ingest --source pubmed --batch file.ndjson --resume
```

**Before (Modern)**:

```bash
med-ingest pubmed --batch-file file.ndjson --continue-from-ledger
```

**After (Unified)**:

```bash
med ingest pubmed --batch file.ndjson --resume
```

---

## Success Metrics

### Overall Success Criteria

- [ ] Single CLI interface (`med ingest`)
- [ ] 100% feature parity with both legacy CLIs
- [ ] >95% user adoption of unified CLI
- [ ] ~500 lines of duplicate code removed
- [ ] Zero critical bugs in unified CLI
- [ ] Complete documentation and migration guide

### Phase-Specific Metrics

**Phase 1**:

- [ ] Both CLIs use shared helpers
- [ ] 50%+ code duplication eliminated
- [ ] No user-facing changes

**Phase 2**:

- [ ] Unified CLI supports all workflows
- [ ] >95% adoption after 3 months
- [ ] Migration guide published and followed

**Phase 3**:

- [ ] Legacy code removed
- [ ] Test suite simplified
- [ ] Documentation cleaned up

---

## Risk Mitigation

### High-Risk Items

1. **User migration resistance** → Clear communication, extended timeline
2. **Feature parity gaps** → Comprehensive testing, user feedback
3. **Breaking unmigrated users** → Verify >95% adoption first

### Rollback Plans

- **Phase 1**: Easy (revert refactoring)
- **Phase 2**: Medium (disable unified CLI, keep legacy)
- **Phase 3**: Hard (emergency release restoring legacy)

---

## Total Scope

### Development Effort

- **Active development**: 6-10 weeks (1 FTE)
- **Migration period**: 12 weeks (monitoring/support)
- **Total timeline**: 22 weeks (~5.5 months)

### Code Changes

- **New code**: ~700 lines (helpers + unified CLI)
- **Refactored code**: ~300 lines (both existing CLIs)
- **Removed code**: ~500 lines (legacy CLI + delegates)
- **Net reduction**: ~100 lines + improved maintainability

### Documentation

- **New docs**:
  - CLI_UNIFICATION_ROADMAP.md (40 pages)
  - Migration guide (~10 pages)
  - Unified CLI reference (~15 pages)
- **Updated docs**:
  - `docs/ingestion_runbooks.md`
  - `docs/operations_manual.md`
  - `README.md`
  - `CONTRIBUTING.md`

---

## Next Steps

1. **Review**: Stakeholders review proposals and roadmap
2. **Approve**: Sign off on Phase 1 implementation
3. **Schedule**: Allocate 2-3 weeks for Phase 1 work
4. **Implement**: Execute `extract-ingestion-cli-shared-helpers` proposal
5. **Validate**: Run full test suite, deploy to staging
6. **Deploy**: Production deployment of Phase 1
7. **Plan**: Review Phase 1 results, plan Phase 2 start

---

## Files Created

```
openspec/changes/
├── extract-ingestion-cli-shared-helpers/
│   ├── proposal.md
│   ├── tasks.md (88 tasks)
│   └── specs/ingestion/spec.md
├── implement-unified-ingestion-cli/
│   ├── proposal.md
│   ├── tasks.md (106 tasks)
│   ├── design.md
│   └── specs/ingestion/spec.md
└── remove-legacy-ingestion-cli/
    ├── proposal.md
    ├── tasks.md (93 tasks)
    └── specs/ingestion/spec.md

Documentation/
├── CLI_UNIFICATION_ROADMAP.md (comprehensive guide)
└── CLI_UNIFICATION_SUMMARY.md (this file)
```

**Total**: 11 files created, all proposals validated ✅

---

## Questions?

- **Technical details**: See individual proposal files
- **Implementation timeline**: See CLI_UNIFICATION_ROADMAP.md
- **Risk assessment**: See roadmap Risk Management section
- **Communication plan**: See roadmap Communication Plan section

---

**Status**: ✅ All proposals created and validated
**Ready for**: Stakeholder review and Phase 1 approval
**Created**: 2025-10-03
**Version**: 1.0
