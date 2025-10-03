# Reduce Ingestion Runtime Validation

## Why

The ingestion module contains 46 calls to `ensure_json_mapping()` and `ensure_json_sequence()` runtime validation helpers across adapters. With properly typed adapters using TypedDict contracts, many of these calls become redundant—the type system already guarantees the structure. Excessive runtime validation adds overhead, obscures actual validation logic, and indicates weak upstream typing. Keeping validation only at external API boundaries (HTTP response parsing) aligns with type-driven design.

## What Changes

- Audit all 46 `ensure_json_mapping/sequence` calls to categorize as:
  - **Boundary validation** (at `fetch_json()` return sites where external JSON is first parsed): KEEP
  - **Internal redundancy** (within typed adapter methods where TypedDict already guarantees structure): REMOVE
- Remove redundant calls in `adapters/clinical.py` (reduce 32→~8 calls)
- Remove redundant calls in `adapters/guidelines.py` (reduce 12→~4 calls)
- Remove redundant calls in `adapters/literature.py` (currently 2, likely keep both at boundaries)
- Document remaining validation usage in module docstrings as "external boundary validation"
- Add API version/schema expectations in comments where validation is kept

## Impact

- **Affected specs**: `ingestion` (modifies validation approach)
- **Affected code**:
  - `src/Medical_KG/ingestion/adapters/clinical.py` (reduce ~24 calls)
  - `src/Medical_KG/ingestion/adapters/guidelines.py` (reduce ~8 calls)
  - `src/Medical_KG/ingestion/utils.py` (potentially add deprecation notice)
- **Benefits**: Cleaner code, reduced runtime overhead, clearer separation of boundary vs internal validation
- **Risks**: If external API changes format, may surface later in pipeline; mitigated by keeping validation at fetch boundaries
- **Coordination**: Should complete after `complete-ingestion-adapter-type-params` to ensure TypedDict guarantees are in place
