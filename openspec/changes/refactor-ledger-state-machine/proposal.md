# Refactor Ledger to State Machine with Compaction

## Why

The current ledger implementation has critical issues:

**Unbounded Growth**:

- Loads entire JSONL history into memory at startup
- Long-running environments accumulate millions of rows
- Initialization time grows linearly with history size (O(n))
- No compaction mechanism

**Implicit State Model**:

- States are free-form strings ("pdf_ir_ready", "auto_done", "schema_failed")
- Magic literals sprinkled across codebase
- No validation of state transitions
- Hard to discover valid states
- Impossible to prevent invalid transitions

**Poor Auditability**:

- State changes are opaque strings
- No structured error metadata
- Hard to build operational dashboards
- Triage requires reading logs

From `repo_optimization_opportunities.md`: "The JSONL ledger loads every historical entry into `_latest` at startup and exposes states as free-form strings; long-running ingest environments will accumulate hundreds of thousands of rows and rely on implicit literals that are sprinkled across services."

## What Changes

### Introduce Explicit State Machine

```python
class LedgerState(str, Enum):
    """Valid ledger states with explicit transitions."""
    PENDING = "pending"
    FETCHING = "fetching"
    FETCHED = "fetched"
    PARSING = "parsing"
    PARSED = "parsed"
    VALIDATING = "validating"
    VALIDATED = "validated"
    IR_BUILDING = "ir_building"
    IR_READY = "ir_ready"
    FAILED = "failed"
    RETRYING = "retrying"
    COMPLETED = "completed"
    SKIPPED = "skipped"

VALID_TRANSITIONS: dict[LedgerState, set[LedgerState]] = {
    LedgerState.PENDING: {LedgerState.FETCHING, LedgerState.SKIPPED},
    LedgerState.FETCHING: {LedgerState.FETCHED, LedgerState.FAILED},
    # ... complete transition graph
}
```

### Add Compaction Support

- **Snapshot**: Periodic full state snapshot (e.g., daily)
- **Delta log**: Only recent changes since snapshot
- **Initialization**: Load snapshot + apply deltas
- **Result**: O(1) startup time regardless of history

### Structured Audit Records

```python
@dataclass
class LedgerAuditRecord:
    doc_id: str
    old_state: LedgerState
    new_state: LedgerState
    timestamp: float
    adapter: str
    error_type: str | None
    error_message: str | None
    retry_count: int
    metadata: dict[str, Any]
```

### Migration Path

- Parse existing string states to enum (best-effort)
- Unknown states map to special LEGACY state
- Write new entries with enum values
- Provide migration script for production ledgers

## Impact

- **Affected specs**: ingestion (ledger interface changes)
- **Affected code**:
  - `src/Medical_KG/ingestion/ledger.py` (major refactor, ~300 lines changed)
  - `src/Medical_KG/ingestion/models.py` (add state machine types, +100 lines)
  - `src/Medical_KG/pdf/service.py` (update state literals to enum, ~20 lines)
  - All services using ledger (update state references)
  - `tests/ingestion/test_ledger.py` (comprehensive state machine tests)
  - Migration script for production ledgers
- **Benefits**:
  - **Bounded startup**: O(1) initialization regardless of history
  - **Type-safe states**: Compiler prevents invalid transitions
  - **Rich auditing**: Structured records enable dashboards
  - **Discoverable**: IDE autocomplete for valid states
- **Breaking changes**: **YES** - string states become enum
  - Mitigation: Migration script, backwards-compatible parsing
- **Risk**: High - core infrastructure change, data migration required
