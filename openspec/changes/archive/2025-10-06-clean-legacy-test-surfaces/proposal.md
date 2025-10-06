# Proposal: Clean Legacy Test Surfaces

## Why

Several test modules still construct legacy artifacts (legacy ledgers, `LegacyValidator` assertions, untyped payloads, deprecated API fixtures) that will fail once the preceding legacy retirement scopes land. These tests create maintenance burden, slow CI, and provide false coverage for unsupported code paths. Cleaning them proactively prevents CI breakage and keeps the test suite focused on current functionality.

## What Changes

- **Delete legacy test fixtures**: Remove test data for deprecated features
- **Rewrite compatibility tests**: Replace with tests for current API
- **Remove deprecated API tests**: Delete tests for removed methods/classes
- **Add replacement smoke tests**: Cover streaming, enum-only, typed flows
- **Purge legacy test helpers**: Remove helper functions for deprecated features
- **Update test documentation**: Focus on current testing patterns

## Impact

**Affected specs**: `ingestion` (test infrastructure)

**Affected code**:

- `tests/ingestion/test_pipeline.py` - Remove legacy wrapper tests (~80 lines)
- `tests/config/test_schema_validator.py` - Remove `LegacyValidator` tests (~60 lines)
- `tests/fixtures/` - Delete legacy JSONL/config files (~10 files)
- `tests/ingestion/test_ledger.py` - Remove string state tests (~40 lines)
- `tests/ir/test_builder.py` - Remove untyped payload tests (~50 lines)
- `tests/test_http_client.py` - Remove noop metric tests (~30 lines)

**Breaking Change**: NO - only affects test suite, not production code

**Migration Path**: N/A - internal test refactoring

**Benefits**:

- -260 lines of outdated test code removed
- ~10 obsolete fixture files deleted
- Faster CI execution (fewer redundant tests)
- Higher quality coverage (tests reflect actual usage)
- Clearer test suite structure
- Prevents confusion for new contributors
- Reduces maintenance burden
