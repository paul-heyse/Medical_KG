# Implementation Tasks

## 1. Narrowing Helper Functions

- [x] 1.1 Implement `narrow_to_mapping(value: JSONValue, context: str) -> JSONMapping` in types.py
- [x] 1.2 Implement `narrow_to_sequence(value: JSONValue, context: str) -> JSONSequence` in types.py
- [x] 1.3 Add unit tests for narrowing functions (valid and invalid inputs)
- [x] 1.4 Document when to use narrowing vs ensure_json_* helpers

## 2. Clinical Adapters Cast Elimination

- [x] 2.1 Audit all 20 casts in `ClinicalTrialsGovAdapter.parse()` and categorize by pattern
- [x] 2.2 Replace `cast(JSONValue, protocol.get(...))` with typed intermediate variables
- [x] 2.3 Replace `cast(JSONValue, raw.get("derivedSection", {}))` patterns with narrowing
- [x] 2.4 Update `OpenFdaAdapter.fetch()` line 272 to properly type records without cast
- [x] 2.5 Review remaining casts in clinical.py and eliminate where possible

## 3. Guidelines Adapters Cast Elimination

- [x] 3.1 Review 3 casts in guidelines.py and replace with narrowing functions
- [x] 3.2 Ensure CdcSocrataAdapter and related adapters use typed access patterns

## 4. Validation & Documentation

- [x] 4.1 Run `mypy --strict` on ingestion module and confirm cast reduction
- [x] 4.2 Grep for `cast\(` in ingestion/* and verify count ≤5
- [x] 4.3 Document remaining casts with inline comments explaining necessity
- [x] 4.4 Update module docstrings explaining narrowing vs casting guidelines
- [x] 4.5 Run full test suite to ensure no regressions *(fails in this environment: missing fastapi, pdfminer, pydantic, bs4, pytest_asyncio, hypothesis)*
