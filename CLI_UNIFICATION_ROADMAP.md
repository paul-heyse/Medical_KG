# CLI Unification Roadmap

## Executive Summary

The Medical_KG project maintains two parallel ingestion CLIs with duplicated functionality. This roadmap provides a **3-phase, low-risk migration path** to a single, unified CLI interface.

### Current State

- **Legacy CLI**: `Medical_KG.cli` → `med ingest` command (Click-based)
- **Modern CLI**: `Medical_KG.ingestion.cli` → `med-ingest` command (Typer-based)
- **Problem**: Duplicated code, inconsistent behavior, user confusion

### Target State

- **Single CLI**: `med ingest <adapter> [options]` (Typer-based)
- **Benefits**: Consistent UX, reduced maintenance, clearer documentation
- **Timeline**: 4-7 months total (3-month migration period required)

## Three-Phase Approach

### Phase 1: Extract Shared Helpers (Non-Breaking) ✅

**Proposal**: `extract-ingestion-cli-shared-helpers`

**Duration**: 2-3 weeks

**Risk**: 🟢 Low (pure refactoring)

**What**:

- Create `src/Medical_KG/ingestion/cli_helpers.py` with shared functions
- Both CLIs use common helpers
- No user-facing changes
- Comprehensive test coverage

**Why First**:

- Non-breaking foundation
- Immediate value (reduces duplication)
- De-risks future phases
- Can be deployed independently

**Deliverables**:

- Shared helper module (~300 lines)
- Both CLIs refactored to use helpers
- Test suite updated
- Documentation updated

**Key Functions**:

- `load_ndjson_batch()`: NDJSON parsing
- `invoke_adapter()`: Adapter invocation
- `format_cli_error()`: Error formatting
- `handle_ledger_resume()`: Resume logic
- `format_results()`: Output formatting

---

### Phase 2: Implement Unified CLI (Soft Breaking) ⚠️

**Proposal**: `implement-unified-ingestion-cli`

**Duration**: 3-5 weeks + 3-month migration period

**Risk**: 🟡 Medium (user-facing changes)

**What**:

- New unified CLI: `med ingest <adapter> [options]`
- All features from both legacy and modern CLIs
- Deprecated command delegates with warnings
- Rich progress bars and better UX
- Migration guide and tooling

**Why Second**:

- Requires shared helpers foundation
- Users need time to migrate
- Deprecation warnings allow gradual adoption
- Can coexist with legacy during migration

**Deliverables**:

- Unified CLI implementation (~400 lines)
- Deprecation delegates (~50 lines)
- Comprehensive tests (~300 lines)
- Migration guide and documentation
- Adoption tracking metrics

**Migration Timeline**:

1. **Month 0**: Release with warnings
2. **Month 1**: Migration guide published
3. **Month 2**: CI/CD updated, monitoring adoption
4. **Month 3**: Final migration deadline communicated

**Command Structure**:

```bash
# Before (legacy)
med ingest --source pubmed --batch file.ndjson --resume

# Before (modern)
med-ingest pubmed --batch-file file.ndjson --continue-from-ledger

# After (unified)
med ingest pubmed --batch file.ndjson --resume
```

---

### Phase 3: Remove Legacy CLI (Hard Breaking) 🔴

**Proposal**: `remove-legacy-ingestion-cli`

**Duration**: 1-2 weeks

**Risk**: 🔴 High for unmigrated users, 🟢 Low for migrated users

**What**:

- Delete legacy CLI code and delegates
- Remove deprecation warnings (commands don't exist)
- Clean up tests and documentation
- Major version bump (e.g., 2.0.0)

**Why Last**:

- Requires successful migration (>95% adoption)
- Minimum 3 months after Phase 2 release
- Completes the unification
- Eliminates technical debt

**Prerequisites**:

- ✅ >95% adoption of unified CLI
- ✅ 3+ months since deprecation warnings
- ✅ Zero critical bugs in unified CLI
- ✅ Internal tooling migrated
- ✅ Final communication sent (2 weeks prior)

**Deliverables**:

- ~500 lines of dead code removed
- Simplified test suite
- Updated documentation (no migration guides)
- Major version release

---

## Implementation Sequence

### Detailed Timeline

```
┌─────────────────────────────────────────────────────────────┐
│ Phase 1: Extract Shared Helpers (Weeks 1-3)                │
├─────────────────────────────────────────────────────────────┤
│ Week 1: Analysis, design, create cli_helpers.py            │
│ Week 2: Refactor both CLIs, add tests                      │
│ Week 3: Documentation, review, deploy                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 2: Unified CLI + Migration (Weeks 4-8 + 12 weeks)    │
├─────────────────────────────────────────────────────────────┤
│ Week 4-5: Design and implement unified CLI                 │
│ Week 6: Add deprecation delegates and warnings             │
│ Week 7: Testing and documentation                          │
│ Week 8: Deploy with deprecation warnings                   │
│                                                             │
│ Weeks 9-20: 3-month migration period                       │
│   - Monitor adoption metrics                               │
│   - Support user migration                                 │
│   - Update internal tooling                                │
│   - Collect feedback                                       │
└─────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Phase 3: Remove Legacy CLI (Weeks 21-22)                   │
├─────────────────────────────────────────────────────────────┤
│ Week 21: Validate adoption, remove legacy code             │
│ Week 22: Major version release, monitor                    │
└─────────────────────────────────────────────────────────────┘
```

**Total Duration**: 22 weeks (~5.5 months)

### Dependencies

```
Phase 1 (extract-ingestion-cli-shared-helpers)
    ↓ (blocks)
Phase 2 (implement-unified-ingestion-cli)
    ↓ (3-month migration period + >95% adoption)
Phase 3 (remove-legacy-ingestion-cli)
```

**Critical Path**: Must complete sequentially. No parallel execution.

---

## Risk Management

### Phase 1 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Helper abstraction too complex | Medium | Start simple, iterate |
| Both CLIs break | High | Comprehensive integration tests |
| Performance regression | Low | Benchmark before/after |

### Phase 2 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Users don't migrate | High | Clear warnings, migration tools |
| Feature parity gaps | High | Feature matrix, integration tests |
| Confusing UX | Medium | User testing, clear help text |

### Phase 3 Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Unmigrated users broken | High | Verify >95% adoption first |
| Rollback needed | Medium | Clear rollback procedure |
| Documentation stale | Low | Comprehensive update in Phase 2 |

---

## Success Metrics

### Phase 1 Success Criteria

- [ ] `cli_helpers.py` module created with 5+ helper functions
- [ ] Both CLIs use shared helpers
- [ ] All existing tests pass
- [ ] No user-facing behavior changes
- [ ] Code duplication reduced by 50%+

### Phase 2 Success Criteria

- [ ] Single `med ingest` command with all features
- [ ] Deprecation warnings display correctly
- [ ] Migration guide published
- [ ] >95% adoption after 3 months
- [ ] Zero critical bugs reported

### Phase 3 Success Criteria

- [ ] Legacy CLI code removed (~500 lines)
- [ ] Test suite simplified
- [ ] Documentation clean (no migration guides)
- [ ] Major version released
- [ ] No rollback required

---

## Resource Requirements

### Development Effort

**Phase 1**: 2-3 weeks (1 FTE)

- Analysis: 2 days
- Implementation: 5 days
- Testing: 3 days
- Documentation: 2 days

**Phase 2**: 3-5 weeks (1 FTE) + monitoring during migration

- Design: 3 days
- Implementation: 10 days
- Testing: 4 days
- Documentation: 5 days
- Migration support: Ongoing (part-time for 3 months)

**Phase 3**: 1-2 weeks (1 FTE)

- Validation: 2 days
- Removal: 3 days
- Testing: 2 days
- Documentation: 1 day

**Total**: 6-10 weeks active development + 3 months migration period

### Coordination Requirements

- **Phase 1**: Low (internal refactoring)
- **Phase 2**: High (user communication, migration support)
- **Phase 3**: Medium (final communication, monitoring)

---

## Communication Plan

### Phase 1 (Internal)

- Team announcement: "Refactoring CLI internals"
- No user communication needed (non-breaking)
- Update internal docs

### Phase 2 (User-Facing)

**Launch (Week 8)**:

- Blog post: "Introducing Unified CLI"
- Email to users: "New CLI available"
- Documentation update: Migration guide

**Month 1**:

- Progress update: "X% migrated"
- Office hours for migration questions
- FAQ updates based on feedback

**Month 2**:

- Second reminder: "1 month until migration deadline"
- CI scripts audit and update guide
- Success stories from early adopters

**Month 3**:

- Final reminder: "Legacy CLI removal in 2 weeks"
- Last call for migration support
- Announce Phase 3 timeline

### Phase 3 (Breaking Change)

**2 Weeks Before**:

- Major version announcement
- Breaking change notice
- Rollback instructions

**Release Day**:

- Release notes with explicit removed commands
- Support channel monitoring
- Quick response to issues

**1 Week After**:

- Adoption metrics report
- Lessons learned blog post
- Community feedback collection

---

## OpenSpec Proposal Summary

### Proposal 1: extract-ingestion-cli-shared-helpers ✅

**Status**: ✅ Validated with `--strict`

**Files**:

- `proposal.md`: Why, what, impact
- `tasks.md`: 84 implementation tasks
- `specs/ingestion/spec.md`: Requirements for shared helpers

**Validation**:

```bash
openspec validate extract-ingestion-cli-shared-helpers --strict
# ✅ Change 'extract-ingestion-cli-shared-helpers' is valid
```

### Proposal 2: implement-unified-ingestion-cli ✅

**Status**: ✅ Validated with `--strict`

**Files**:

- `proposal.md`: Why, what, impact, migration
- `tasks.md`: 101 implementation tasks
- `design.md`: Technical decisions (11KB)
- `specs/ingestion/spec.md`: Requirements for unified CLI

**Validation**:

```bash
openspec validate implement-unified-ingestion-cli --strict
# ✅ Change 'implement-unified-ingestion-cli' is valid
```

### Proposal 3: remove-legacy-ingestion-cli ✅

**Status**: ✅ Validated with `--strict`

**Files**:

- `proposal.md`: Why, what, prerequisites
- `tasks.md`: 90 implementation tasks
- `specs/ingestion/spec.md`: Requirements for removal

**Validation**:

```bash
openspec validate remove-legacy-ingestion-cli --strict
# ✅ Change 'remove-legacy-ingestion-cli' is valid
```

---

## Quick Start Commands

### Validate All Proposals

```bash
for p in extract-ingestion-cli-shared-helpers implement-unified-ingestion-cli remove-legacy-ingestion-cli; do
  openspec validate $p --strict
done
```

### View Specific Proposal

```bash
openspec show extract-ingestion-cli-shared-helpers
openspec show implement-unified-ingestion-cli
openspec show remove-legacy-ingestion-cli
```

### Track Implementation

```bash
# List all CLI unification proposals
openspec list | grep -E "(extract-ingestion|unified-ingestion|remove-legacy)"

# View task progress
cat openspec/changes/extract-ingestion-cli-shared-helpers/tasks.md | grep "^\- \[x\]" | wc -l
```

---

## Decision Points

### Before Starting Phase 1

- [ ] Approval from project stakeholders
- [ ] Resource allocation confirmed (1 FTE for 2-3 weeks)
- [ ] Agreement on shared helper API design

### Before Starting Phase 2

- [ ] Phase 1 successfully deployed to production
- [ ] No regressions from Phase 1
- [ ] Agreement on 3-month migration timeline
- [ ] Communication plan approved
- [ ] Migration tools ready

### Before Starting Phase 3

- [ ] Adoption metrics show >95% using unified CLI
- [ ] Minimum 3 months since Phase 2 release
- [ ] Zero critical bugs in unified CLI
- [ ] All internal tooling migrated
- [ ] Stakeholder approval for major version bump

---

## Rollback Procedures

### Phase 1 Rollback

**Trigger**: Regression in CLI behavior

**Procedure**:

1. Revert to previous version
2. Investigate root cause
3. Fix and redeploy

**Difficulty**: 🟢 Easy (no user-facing changes)

### Phase 2 Rollback

**Trigger**: Critical bug in unified CLI OR adoption < 20% after 1 month

**Procedure**:

1. Disable unified CLI entry point
2. Keep legacy CLIs working
3. Fix unified CLI issues
4. Re-release when ready

**Difficulty**: 🟡 Medium (some users may have migrated)

### Phase 3 Rollback

**Trigger**: Widespread user breakage OR critical missing feature

**Procedure**:

1. Emergency release restoring legacy CLI
2. Extend migration timeline
3. Address issues
4. Plan new Phase 3 attempt

**Difficulty**: 🔴 Hard (requires emergency release)

---

## Frequently Asked Questions

### Why not do this in one phase?

**Answer**: Risk management. Each phase delivers value independently and can be rolled back. A single large change would be risky and difficult to reverse.

### Can we skip Phase 1?

**Answer**: Not recommended. Shared helpers reduce duplication and de-risk Phase 2 implementation by ensuring both CLIs have identical core logic.

### Why 3 months for migration?

**Answer**: Users need time to:

- Discover the deprecation warnings
- Read migration docs
- Update their scripts/CI
- Test changes
- Deploy to production

### What if users don't migrate by Phase 3?

**Answer**: We validate >95% adoption before proceeding. If adoption is low, we extend the timeline or provide additional migration support. Phase 3 only happens when migration is successful.

### Can we make Phase 2 non-breaking?

**Answer**: Phase 2 IS non-breaking—both CLIs work during migration. Phase 3 is where we break by removing the legacy CLI, but only after confirmed adoption.

---

## Next Actions

1. **Review**: Stakeholders review this roadmap and proposals
2. **Approve**: Get sign-off for Phase 1 start
3. **Plan**: Schedule Phase 1 work (2-3 weeks)
4. **Execute**: Implement `extract-ingestion-cli-shared-helpers`
5. **Monitor**: Track completion, review before Phase 2

---

**Document Version**: 1.0
**Created**: 2025-10-03
**Status**: Ready for Review
**Author**: AI Assistant (based on repo_review.md recommendations)
