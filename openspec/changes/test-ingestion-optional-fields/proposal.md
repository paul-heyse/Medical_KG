# Comprehensive Test Coverage for Ingestion Optional Fields

## Why

All adapter payloads use `NotRequired` for optional fields (e.g., `pmcid: NotRequired[str | None]` in PubMed, `status: NotRequired[str | None]` in clinical trials), but the test suite doesn't systematically verify adapter behavior when these fields are present, absent, or None. This creates risk: validation logic may incorrectly assume optional fields exist, or content/metadata generation may fail when fields are missing. Comprehensive coverage ensures adapters handle all field presence combinations correctly.

## What Changes

- For each of 18 adapters with ≥1 NotRequired field, create test cases covering:
  1. **All optional fields present**: Verify normal path with complete data
  2. **All optional fields absent**: Verify adapter handles missing optional data gracefully
  3. **Mixed presence** (realistic scenario): Some optional fields present, others absent
- Add parametrized tests in `tests/ingestion/test_adapters.py` for systematic coverage
- Create new `tests/ingestion/test_optional_fields.py` module dedicated to optional field scenarios
- Update fixtures in `tests/ingestion/fixtures/*.py` to include optional-field variants
- Document which optional fields are "commonly present" (>80% of real data) vs "rarely present" (<20%)

## Impact

- **Affected specs**: `ingestion` (adds testing requirement for optional fields)
- **Affected code**:
  - `tests/ingestion/fixtures/*.py` (add ~68 fixture variants)
  - `tests/ingestion/test_adapters.py` (parametrized optional field tests)
  - `tests/ingestion/test_optional_fields.py` (new module, ~400 lines)
- **Coverage targets**:
  - Terminology: 6 adapters × 3 scenarios = 18 test cases
  - Clinical: 3 adapters × 8 scenarios = 24 test cases
  - Literature: 3 adapters × 4 scenarios = 12 test cases
  - Guidelines: 2 adapters × 3 scenarios = 6 test cases
  - Knowledge: 4 adapters × 2 scenarios = 8 test cases
  - **Total**: ~68 new test cases
- **Benefits**: Catches optional field bugs, documents expected behavior, improves robustness
