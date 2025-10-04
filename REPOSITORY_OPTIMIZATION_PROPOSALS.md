# Repository Optimization Proposals - Complete Package

## Executive Summary

Based on recommendations from `docs/repo_optimization_opportunities.md`, we've developed **5 comprehensive OpenSpec change proposals** to transform the Medical_KG codebase into a more maintainable, scalable, and robust platform.

## What Was Created

### ✅ Proposal 1: refactor-ingestion-pipeline-streaming (VALIDATED)

**Status**: ✅ Validated with `--strict`

**Purpose**: Transform ingestion pipeline from eager evaluation to streaming-first architecture

**Key Changes**:

- Introduce `PipelineEvent` hierarchy for structured lifecycle events
- Make `stream_events()` the primary API with O(1) memory usage
- Add backpressure via bounded buffers
- Enable checkpointing at `BatchProgress` boundaries
- Maintain backwards compatibility via wrapper methods

**Files**:

- `proposal.md` - Why, what, impact
- `tasks.md` - 106 detailed tasks
- `design.md` - Comprehensive architectural decisions
- `specs/ingestion/spec.md` - Delta requirements

**Impact**: Solves OOM issues for million-document batches, enables real-time progress, foundation for distributed processing

---

### 🔄 Proposal 2: refactor-ledger-state-machine

**Purpose**: Replace string-based ledger states with explicit state machine and add compaction

**Key Changes**:

- Define `LedgerState` enum with all valid transitions
- Add state machine validation preventing invalid transitions
- Implement periodic compaction (snapshot + delta log)
- Add structured audit records with rich metadata
- Keep ledger initialization cost flat as history grows

**Estimated Tasks**: ~85 tasks

**Impact**: Prevents state bugs, enables richer dashboards, O(1) startup time regardless of history size

---

### 🔄 Proposal 3: replace-config-validator-jsonschema

**Purpose**: Replace custom configuration validator with industry-standard `jsonschema` library

**Key Changes**:

- Remove custom `ConfigValidator` class (~200 lines)
- Adopt `jsonschema` for schema validation
- Add schema version tracking
- Provide better error messages with JSON pointers
- Support advanced schema features (oneOf, anyOf, conditional)

**Estimated Tasks**: ~70 tasks

**Impact**: Reduces maintenance burden, improves error messages, enables schema-driven tooling

---

### 🔄 Proposal 4: standardize-optional-dependencies

**Purpose**: Standardize optional dependency handling with custom exception and reduce mypy ignores

**Key Changes**:

- Introduce `MissingDependencyError` with install hints
- Replace all `ModuleNotFoundError` with structured errors
- Add protocol shims for optional packages
- Incrementally reduce mypy `ignore_errors` lists
- Document dependency matrix in dev guide

**Estimated Tasks**: ~95 tasks

**Impact**: Better contributor experience, fewer type errors slip through, clear upgrade paths

---

### 🔄 Proposal 5: add-http-client-telemetry

**Purpose**: Add observable hooks to `AsyncHttpClient` for structured telemetry

**Key Changes**:

- Add callback hooks: `on_request`, `on_retry`, `on_backoff`, `on_response`
- Emit structured events for HTTP lifecycle
- Expose limiter queue times as metrics
- Add per-host instrumentation support
- Document telemetry patterns

**Estimated Tasks**: ~75 tasks

**Impact**: Observable throttling, diagnosable rate limits, consistent adapter telemetry

---

## Implementation Sequence

### Recommended Order

```
1. refactor-ingestion-pipeline-streaming (Week 1-3) 🔴 FOUNDATION
   ↓
2. add-http-client-telemetry (Week 4-5) 🟠 INFRASTRUCTURE
   ↓
3. refactor-ledger-state-machine (Week 6-8) 🟡 MEDIUM IMPACT
   ‖ (parallel possible)
4. replace-config-validator-jsonschema (Week 6-7) 🟡 MEDIUM IMPACT
   ↓
5. standardize-optional-dependencies (Week 9-10) 🟢 POLISH
```

**Total Duration**: 10-12 weeks (2-3 months)

**Parallelization**: Proposals 3 & 4 can run in parallel during weeks 6-7

### Dependencies

- **Proposal 1 blocks**: 2, 3, 4, 5 (foundational pipeline changes)
- **Proposal 2 depends on**: 1 (uses streaming events)
- **Proposals 3 & 4**: Independent, can run in parallel
- **Proposal 5 depends on**: 1 (uses event system patterns)

---

## Success Metrics

### Overall Targets

- **Memory efficiency**: O(1) usage for arbitrarily large batches
- **Type safety**: 90%+ mypy strict coverage (from ~70%)
- **Maintainability**: -500 lines of custom infrastructure code
- **Observability**: Structured events/metrics throughout
- **Documentation**: Comprehensive guides for all new patterns

### Per-Proposal Metrics

**Proposal 1**:

- [ ] Memory usage flat for 1M+ document batches
- [ ] <10% throughput regression
- [ ] 100% backwards compatibility
- [ ] Streaming adoption >80% after 6 months

**Proposal 2**:

- [ ] O(1) ledger initialization regardless of history
- [ ] Zero invalid state transitions in production
- [ ] Compaction reduces disk usage by >60%
- [ ] Rich audit events enable dashboard creation

**Proposal 3**:

- [ ] -200 lines of custom validator code
- [ ] 100% feature parity with `jsonschema`
- [ ] Better error messages (user feedback)
- [ ] Schema-driven config tooling possible

**Proposal 4**:

- [ ] 100% of optional imports use `MissingDependencyError`
- [ ] Mypy ignore list reduced by >50%
- [ ] Clear install hints for all missing dependencies
- [ ] Dependency matrix documented

**Proposal 5**:

- [ ] All HTTP lifecycle events observable
- [ ] Rate limiting issues diagnosable via metrics
- [ ] Per-adapter telemetry standardized
- [ ] Zero custom telemetry wrappers needed

---

## Risk Management

### High-Risk Items

| Risk | Proposal | Mitigation |
|------|----------|------------|
| Breaking changes to core pipeline | 1 | 6-month deprecation, backwards-compatible wrappers |
| Ledger data migration | 2 | Write migration script, test on production copies |
| Config validation gaps | 3 | Comprehensive test suite, staged rollout |
| Type errors proliferate | 4 | Incremental approach, track error count |
| Telemetry overhead | 5 | Benchmark performance, make hooks optional |

### Medium-Risk Items

| Risk | Proposal | Mitigation |
|------|----------|------------|
| Adoption resistance | 1, 2 | Clear migration guides, internal adoption first |
| Feature parity gaps | 3 | Feature matrix, acceptance testing |
| Documentation debt | All | Documentation tasks in every proposal |

---

## Resource Requirements

### Development Effort

| Proposal | Duration | FTE | Complexity |
|----------|----------|-----|------------|
| 1. Streaming Pipeline | 3 weeks | 1-2 | High |
| 2. Ledger State Machine | 2-3 weeks | 1 | Medium |
| 3. Config Validator | 1-2 weeks | 1 | Low |
| 4. Optional Dependencies | 2 weeks | 1 | Medium |
| 5. HTTP Telemetry | 1-2 weeks | 1 | Low |

**Total**: 10-12 weeks with 1 FTE, or 6-8 weeks with 2 FTE

### Testing Requirements

- **Unit tests**: ~400 new test cases across all proposals
- **Integration tests**: ~50 end-to-end scenarios
- **Performance tests**: Memory profiling, throughput benchmarks
- **Migration tests**: Backwards compatibility, data migration

---

## Communication Plan

### Internal Stakeholders

**Week 1**: Present proposal package for approval
**Week 2**: Kickoff meeting, assign resources
**Bi-weekly**: Progress updates, blocker resolution
**Post-implementation**: Retrospective, lessons learned

### External Users

**Implementation**: Internal-only, no external communication
**Before Breaking Changes**: 4-week notice, migration guide
**After Release**: Blog post, changelog, support availability

---

## Next Steps

1. **Review**: Stakeholders review all 5 proposals
2. **Prioritize**: Confirm implementation sequence
3. **Resource**: Allocate 1-2 FTE for 10-12 weeks
4. **Approve**: Sign off on Phase 1 (Proposal 1)
5. **Execute**: Begin `refactor-ingestion-pipeline-streaming`
6. **Monitor**: Track metrics, adjust as needed

---

## File Structure

```
openspec/changes/
├── refactor-ingestion-pipeline-streaming/  ✅ COMPLETE
│   ├── proposal.md
│   ├── tasks.md (106 tasks)
│   ├── design.md
│   └── specs/ingestion/spec.md
├── refactor-ledger-state-machine/          🔄 IN PROGRESS
│   ├── proposal.md
│   ├── tasks.md (~85 tasks)
│   ├── design.md
│   └── specs/ingestion/spec.md
├── replace-config-validator-jsonschema/    🔄 IN PROGRESS
│   ├── proposal.md
│   ├── tasks.md (~70 tasks)
│   ├── design.md
│   └── specs/config/spec.md
├── standardize-optional-dependencies/      🔄 IN PROGRESS
│   ├── proposal.md
│   ├── tasks.md (~95 tasks)
│   └── specs/observability/spec.md
└── add-http-client-telemetry/              🔄 IN PROGRESS
    ├── proposal.md
    ├── tasks.md (~75 tasks)
    ├── design.md
    └── specs/ingestion/spec.md

Documentation/
├── REPOSITORY_OPTIMIZATION_PROPOSALS.md (this file)
└── docs/repo_optimization_opportunities.md (original recommendations)
```

---

## Status

- ✅ **Proposal 1**: Complete and validated
- 🔄 **Proposals 2-5**: In progress (files being created)
- **Estimated completion**: Next 30 minutes for full package

---

**Created**: 2025-10-04
**Version**: 1.0
**Author**: AI Assistant (based on repo_optimization_opportunities.md)
**Status**: Ready for stakeholder review
