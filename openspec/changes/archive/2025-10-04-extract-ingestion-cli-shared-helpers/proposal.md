# Extract Shared Ingestion CLI Helpers

## Why

The Medical_KG project has two parallel ingestion CLIs:

1. **Legacy CLI** (`Medical_KG.cli` - `med ingest` command)
2. **Modern Typer CLI** (`Medical_KG.ingestion.cli`)

Both implement similar functionality independently, causing:

- **Code duplication**: NDJSON parsing, adapter invocation, error handling duplicated
- **Maintenance burden**: Bug fixes must be applied twice
- **Drift risk**: Implementations diverge over time (already happening with validation)
- **Inconsistent behavior**: Different error messages, validation rules, edge case handling

Repository review notes: "The legacy `med ingest` command reimplements batching, adapter invocation, and JSON parsing separately from the new Typer-based CLI, still lacking the richer validation we just added."

This is the **foundation phase** for CLI unification. Extracting shared helpers is:

- **Non-breaking**: Both CLIs continue to work
- **Low risk**: Pure refactoring with test coverage
- **Immediate value**: Reduces duplication, enables consistent improvements

## What Changes

### Create Shared Helper Module

- New module: `src/Medical_KG/ingestion/cli_helpers.py`
- Extract common operations used by both CLIs:
  - `load_ndjson_batch()`: Parse and validate NDJSON files
  - `invoke_adapter()`: Instantiate and execute adapters
  - `format_cli_error()`: Consistent error message formatting
  - `handle_ledger_resume()`: Ledger-based resume logic
  - `format_results()`: Output formatting for success/failure

### Refactor Both CLIs to Use Helpers

- Update `Medical_KG.cli` (legacy) to use shared helpers
- Update `Medical_KG.ingestion.cli` (modern) to use shared helpers
- Remove duplicated code from both CLIs
- Maintain identical external behavior (no breaking changes)

### Add Comprehensive Tests

- Unit tests for each shared helper function
- Integration tests verifying both CLIs work with helpers
- Regression tests ensuring behavior unchanged
- Edge case coverage (malformed JSON, network errors, etc.)

### Documentation

- Document shared helpers module (docstrings, examples)
- Add architecture diagram showing CLI → helpers → adapters flow
- Update developer guide with helper usage patterns

## Impact

- **Affected specs**: None (internal refactoring)
- **Affected code**:
  - `src/Medical_KG/ingestion/cli_helpers.py` (new, ~300 lines)
  - `src/Medical_KG/cli.py` (refactor, -150 lines, +50 lines)
  - `src/Medical_KG/ingestion/cli.py` (refactor, -120 lines, +40 lines)
  - `tests/ingestion/test_cli_helpers.py` (new, ~250 lines)
  - `tests/ingestion/test_cli.py` (update regression tests)
  - `docs/ingestion_runbooks.md` (+30 lines for helpers)
- **Benefits**:
  - **Single source of truth**: Fixes/improvements apply to both CLIs
  - **Consistent behavior**: Same validation, error handling everywhere
  - **Easier testing**: Test helpers once, benefits both CLIs
  - **Foundation for unification**: Enables future CLI consolidation
- **Breaking changes**: None
- **Risk**: Low - pure refactoring with test coverage
