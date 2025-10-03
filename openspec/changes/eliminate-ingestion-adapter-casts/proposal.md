# Eliminate Ingestion Adapter Casts

## Why

The ingestion module contains 29 `typing.cast()` calls across adapters, indicating type system workarounds rather than proper type-driven design. The majority (20 calls) are concentrated in `ClinicalTrialsGovAdapter.parse()`, where `JSONValue` needs narrowing to `JSONMapping` or `JSONSequence`. With proper TypedDict usage and narrowing helper functions, these casts can be eliminated. Excessive casting defeats static analysis, hides potential bugs, and indicates incomplete type coverage.

## What Changes

- Introduce narrowing helper functions in `ingestion/types.py`:
  - `narrow_to_mapping(value: JSONValue, context: str) -> JSONMapping` (typed, raises TypeError)
  - `narrow_to_sequence(value: JSONValue, context: str) -> JSONSequence` (typed, raises TypeError)
- Replace `cast(JSONValue, raw.get(...))` patterns with TypedDict-aware access
- Refactor `ClinicalTrialsGovAdapter.parse()` to use typed intermediate variables instead of inline casts
- Update `OpenFdaAdapter.fetch()` line 272 to return properly typed records without cast
- Keep minimal casts (≤5) only at true boundary parsing where external API shape is unknown

## Impact

- **Affected specs**: `ingestion` (improves type safety requirement)
- **Affected code**:
  - `src/Medical_KG/ingestion/adapters/clinical.py` (reduce 20→≤3 casts, primarily ClinicalTrialsGovAdapter)
  - `src/Medical_KG/ingestion/adapters/guidelines.py` (reduce 3→≤1 casts)
  - `src/Medical_KG/ingestion/types.py` (add narrowing helpers, ~30 lines)
  - `src/Medical_KG/ingestion/utils.py` (2 casts in ensure_* helpers, keep for boundary validation)
- **Target**: Reduce from 29 to ≤5 casts (83% reduction)
- **Benefits**: Better static analysis, clearer error messages, fewer hidden type mismatches
- **Coordination**: Depends on `complete-ingestion-adapter-type-params` being complete
