# Ledger State Machine Design

## Context

The current ledger stores document processing states as free-form strings in an append-only JSONL file. Every entry is loaded into memory at startup to build the `_latest` state dictionary. This approach has several problems:

- **Unbounded growth**: Production ledgers grow to millions of entries over months
- **Slow initialization**: Startup time increases linearly with ledger size
- **No validation**: Invalid state transitions go undetected
- **Poor discoverability**: Valid states scattered across codebase as string literals
- **Weak auditability**: State changes are opaque strings without context

## Goals

- **Bounded startup**: O(1) initialization regardless of ledger history
- **Type-safe states**: Compile-time validation of state values
- **Validated transitions**: Runtime enforcement of valid state graph
- **Rich audit trail**: Structured records with error context
- **Operational tooling**: Query, validate, and monitor ledger health

## Non-Goals

- **Not changing ledger format**: Still JSONL for compatibility
- **Not distributed ledger**: Single-node append-only log
- **Not event sourcing**: Simple state tracking, not full event history
- **Not removing ledger**: Complementary to, not replacing ledger

## Decisions

### Decision 1: Enum-Based State Model

**Choice**: Define states as Python `Enum` with explicit transition graph

**State Enum**:

```python
class LedgerState(str, Enum):
    """Ledger states with typed values."""
    PENDING = "pending"
    FETCHING = "fetching"
    FETCHED = "fetched"
    PARSING = "parsing"
    PARSED = "parsed"
    VALIDATING = "validating"
    VALIDATED = "validated"
    IR_BUILDING = "ir_building"
    IR_READY = "ir_ready"
    EMBEDDING = "embedding"
    INDEXED = "indexed"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"
    LEGACY = "legacy"  # For unmapped historical states
```

**Transition Graph**:

```python
VALID_TRANSITIONS: dict[LedgerState, set[LedgerState]] = {
    LedgerState.PENDING: {
        LedgerState.FETCHING,
        LedgerState.SKIPPED,
    },
    LedgerState.FETCHING: {
        LedgerState.FETCHED,
        LedgerState.FAILED,
        LedgerState.RETRYING,
    },
    LedgerState.FETCHED: {
        LedgerState.PARSING,
        LedgerState.FAILED,
    },
    # ... complete graph
}

TERMINAL_STATES = {
    LedgerState.COMPLETED,
    LedgerState.FAILED,
    LedgerState.SKIPPED,
}
```

**Rationale**:

- Type-safe: Mypy catches typos and invalid states
- Discoverable: IDE autocomplete shows valid states
- Documented: Enum docstrings explain each state
- Validated: Transition graph prevents invalid flows
- Serializable: `str` mixin ensures JSONL compatibility

**Alternatives considered**:

- **String literals**: Current approach, no validation
- **TypedDict with Literal**: Better than strings, but no runtime validation
- **State pattern classes**: Over-engineered for simple state tracking

### Decision 2: Snapshot + Delta Log Compaction

**Choice**: Periodic snapshots with delta logs, inspired by database WAL

**Format**:

```
ledger/
├── snapshot-2025-10-04.json       # Full state at snapshot time
├── snapshot-2025-10-03.json       # Previous snapshot (kept for rollback)
├── snapshot-2025-10-02.json
├── delta-2025-10-04.jsonl         # Changes since latest snapshot
└── ledger.jsonl                   # Legacy full log (deprecated)
```

**Snapshot Format**:

```json
{
  "version": "1.0",
  "created_at": "2025-10-04T12:00:00Z",
  "document_count": 1234567,
  "states": {
    "doc:123": {
      "state": "completed",
      "updated_at": 1728043200.0,
      "adapter": "pubmed",
      "metadata": {}
    }
  }
}
```

**Loading Algorithm**:

```python
def load_with_compaction(ledger_dir: Path) -> dict[str, DocState]:
    # 1. Find latest snapshot
    snapshot = find_latest_snapshot(ledger_dir)
    states = load_snapshot(snapshot) if snapshot else {}

    # 2. Apply delta log
    delta_file = ledger_dir / f"delta-{snapshot.date}.jsonl"
    for line in delta_file:
        record = json.loads(line)
        states[record["doc_id"]] = record

    return states  # O(1) regardless of history length
```

**Compaction Trigger**:

- Automatic: Daily at midnight (configurable)
- Manual: `med ledger compact` CLI command
- On-demand: After bulk migration or data cleanup

**Rationale**:

- O(1) startup: Load snapshot + deltas, not full history
- Space efficient: Snapshots compress well (gzip)
- Rollback friendly: Keep N previous snapshots
- Simple implementation: No complex LSM tree or compaction strategy

**Alternatives considered**:

- **SQLite**: Adds dependency, query interface overkill
- **Full rewrite**: Loses append-only property, harder to audit
- **No compaction**: Continues to degrade over time

### Decision 3: Structured Audit Records

**Choice**: Dataclass with rich metadata instead of plain strings

**Audit Record**:

```python
@dataclass
class LedgerAuditRecord:
    """Structured ledger state change record."""
    doc_id: str
    old_state: LedgerState
    new_state: LedgerState
    timestamp: float
    adapter: str

    # Error context (if transitioning to FAILED)
    error_type: str | None = None
    error_message: str | None = None
    traceback: str | None = None

    # Retry context
    retry_count: int = 0
    max_retries: int = 3

    # Performance context
    duration_seconds: float | None = None

    # Adapter-specific context
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize for JSONL."""
        return asdict(self)
```

**Benefits**:

- Richer dashboards: Can aggregate by error_type, adapter, duration
- Better triage: Error messages and tracebacks in ledger
- Performance analysis: Duration tracking per state
- Typed: Mypy validates field access

**Rationale**:

- Backwards compatible: Still JSONL, just more structured
- Forward compatible: Can add fields without breaking parsing
- Queryable: Can filter/aggregate on structured fields
- Testable: Dataclass equals works for assertions

### Decision 4: Migration Strategy

**Choice**: In-place migration with backup, not separate ledger

**Migration Process**:

```bash
# 1. Backup original
cp ledger.jsonl ledger.jsonl.backup

# 2. Dry-run validation
med ledger migrate --dry-run --report migration-report.txt

# 3. Actual migration
med ledger migrate --output ledger-migrated.jsonl

# 4. Validate migrated ledger
med ledger validate ledger-migrated.jsonl

# 5. Replace original
mv ledger-migrated.jsonl ledger.jsonl
```

**State Mapping**:

```python
STRING_TO_ENUM: dict[str, LedgerState] = {
    "pending": LedgerState.PENDING,
    "fetching": LedgerState.FETCHING,
    "auto_done": LedgerState.COMPLETED,
    "pdf_ir_ready": LedgerState.IR_READY,
    # Catch-all for unmapped states
    "*": LedgerState.LEGACY,
}
```

**Validation**:

- Check all transitions are valid
- Log warnings for invalid historical transitions
- Count documents by state after migration
- Compare counts with pre-migration for sanity

**Rollback**:

- Keep backup for 30 days
- If issues found, restore from backup
- Migration script is idempotent (can re-run)

**Rationale**:

- Safe: Backup ensures no data loss
- Validated: Dry-run catches issues before migration
- Transparent: Report shows what will change
- Reversible: Can rollback if needed

## Risks / Trade-offs

### Risk 1: Migration Complexity

**Risk**: Migration script has bugs, corrupts ledger

**Mitigation**:

- Comprehensive test suite with realistic data
- Dry-run mode for validation
- Automatic backup before migration
- Rollback procedure documented
- Test on production copy first

### Risk 2: Snapshot Corruption

**Risk**: Snapshot file corrupted, can't load ledger

**Mitigation**:

- Keep N previous snapshots (default 7)
- Can rebuild from full JSONL if needed
- Snapshots are checksummed
- Can fall back to delta-only loading

### Risk 3: State Model Too Rigid

**Risk**: New states needed, graph changes break old code

**Mitigation**:

- Add LEGACY state for unmapped values
- Transition validation is optional (flag to disable)
- Easy to add new states to enum
- Backwards-compatible JSONL format

## Migration Plan

### Phase 1: Implementation (Weeks 1-2)

1. Implement state machine and validation
2. Implement compaction system
3. Add comprehensive tests
4. Update service integrations

### Phase 2: Migration Script (Week 2)

1. Develop migration script
2. Test on synthetic data
3. Test on production copy
4. Dry-run validation

### Phase 3: Staging (Week 3)

1. Deploy to staging
2. Migrate staging ledger
3. Monitor for issues
4. Validate state transitions

### Phase 4: Production (Week 3-4)

1. Schedule maintenance window
2. Backup production ledger
3. Run migration
4. Validate migrated ledger
5. Monitor for 7 days

## Success Criteria

- [ ] Ledger initialization time flat regardless of history
- [ ] All state transitions validated at runtime
- [ ] Migration script tested on production copy
- [ ] Compaction reduces startup time by >90%
- [ ] Zero invalid state transitions in production
- [ ] Operational dashboards use structured audit records
- [ ] Documentation complete with runbooks

## Open Questions

1. **Should we version the state machine?**
   - Proposal: Add version field to snapshots
   - Decision: Yes, start with v1.0

2. **How to handle custom adapter states?**
   - Proposal: Adapters can add metadata, not new states
   - Decision: Keep state set fixed, use metadata for customization

3. **Should compaction be automatic or manual?**
   - Proposal: Automatic daily, with manual override
   - Decision: Automatic with configurable schedule

4. **How long to keep snapshots?**
   - Proposal: Keep last 7 by default, configurable
   - Decision: 7 days sufficient for most rollback scenarios
