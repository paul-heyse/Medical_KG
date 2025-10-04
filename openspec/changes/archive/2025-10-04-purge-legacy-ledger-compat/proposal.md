# Proposal: Purge Legacy Ledger Compatibility Layer

## Why

The `refactor-ledger-state-machine` implementation introduced a `LedgerState` enum with validated transitions, but retained a `LEGACY` enum value and string-to-enum coercion helpers for backwards compatibility during migration. Production ledgers have now been migrated to the enum-based format, making the compatibility layer unnecessary overhead. Removing it eliminates boot-time translation, prevents divergent behavior, and enforces type safety.

## What Changes

- **Remove LEGACY enum value**: Delete `LedgerState.LEGACY` from the enum definition
- **Delete coercion helpers**: Remove functions that accept arbitrary strings and map them to enum values
- **Drop migration script**: Archive `scripts/migrate_ledger_to_state_machine.py` (no longer needed)
- **Update test fixtures**: Rewrite tests to use only valid enum states
- **Compact production ledgers**: Run final compaction to strip legacy markers
- **Enforce enum-only**: Make all ledger operations require `LedgerState` enum values
- **Update documentation**: Remove migration guides and legacy state references

## Impact

**Affected specs**: `ingestion` (ledger state management)

**Affected code**:

- `src/Medical_KG/ingestion/ledger.py` - Remove LEGACY enum and coercion (~60 lines)
- `scripts/migrate_ledger_to_state_machine.py` - Archive migration script (entire file)
- `tests/ingestion/test_pipeline.py` - Update fixtures (~40 lines)
- `tests/test_ingestion_ledger_state_machine.py` - Rewrite legacy state tests (~80 lines)
- `docs/ingestion_runbooks.md` - Remove migration documentation

**Breaking Change**: YES - removes `LedgerState.LEGACY` enum value

**Migration Path**: All production ledgers must be compacted/migrated before deployment

**Benefits**:

- -200 lines of compatibility code removed
- O(1) ledger initialization without string translation
- Type-safe state operations enforced at compile time
- Prevents accidental reintroduction of string-based states
- Simplified state machine with fewer edge cases
- Clearer telemetry and audit logs (no LEGACY markers)
