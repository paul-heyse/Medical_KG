# Implementation Tasks

## 1. Narrowing Helper Functions

- [ ] 1.1 Implement `narrow_to_mapping(value: JSONValue, context: str) -> JSONMapping` in types.py
- [ ] 1.2 Implement `narrow_to_sequence(value: JSONValue, context: str) -> JSONSequence` in types.py
- [ ] 1.3 Add unit tests for narrowing functions (valid and invalid inputs)
- [ ] 1.4 Document when to use narrowing vs ensure_json_* helpers

## 2. Clinical Adapters Cast Elimination

- [ ] 2.1 Audit all 20 casts in `ClinicalTrialsGovAdapter.parse()` and categorize by pattern
- [ ] 2.2 Replace `cast(JSONValue, protocol.get(...))` with typed intermediate variables
- [ ] 2.3 Replace `cast(JSONValue, raw.get("derivedSection", {}))` patterns with narrowing
- [ ] 2.4 Update `OpenFdaAdapter.fetch()` line 272 to properly type records without cast
- [ ] 2.5 Review remaining casts in clinical.py and eliminate where possible

## 3. Guidelines Adapters Cast Elimination

- [ ] 3.1 Review 3 casts in guidelines.py and replace with narrowing functions
- [ ] 3.2 Ensure CdcSocrataAdapter and related adapters use typed access patterns

## 4. Validation & Documentation

- [ ] 4.1 Run `mypy --strict` on ingestion module and confirm cast reduction
- [ ] 4.2 Grep for `cast\(` in ingestion/* and verify count ≤5
- [ ] 4.3 Document remaining casts with inline comments explaining necessity
- [ ] 4.4 Update module docstrings explaining narrowing vs casting guidelines
- [ ] 4.5 Run full test suite to ensure no regressions
