# Implementation Tasks

## 1. Validation Audit & Categorization

- [x] 1.1 List all 32 `ensure_json_*` calls in `adapters/clinical.py` with line numbers and context
- [x] 1.2 List all 12 `ensure_json_*` calls in `adapters/guidelines.py` with line numbers and context
- [x] 1.3 List all 2 `ensure_json_*` calls in `adapters/literature.py` with line numbers and context
- [x] 1.4 Categorize each call as "boundary" (keep) vs "internal redundancy" (remove)
- [x] 1.5 Document decision criteria for each removed call

## 2. Remove Redundant Validation in Clinical Adapters

- [x] 2.1 Remove internal `ensure_json_*` calls in `ClinicalTrialsGovAdapter.parse()` (target: remove 20/32)
- [x] 2.2 Remove internal calls in `OpenFdaAdapter` where TypedDict already guarantees structure
- [x] 2.3 Remove internal calls in `DailyMedAdapter` and `RxNormAdapter`
- [x] 2.4 Keep boundary validation at `fetch()` method return sites

## 3. Remove Redundant Validation in Guidelines Adapters

- [x] 3.1 Remove internal calls in `CdcSocrataAdapter.parse()` (target: remove 8/12)
- [x] 3.2 Remove internal calls in `WhoGhoAdapter` and `OpenPrescribingAdapter`
- [x] 3.3 Keep boundary validation at API response parsing

## 4. Documentation & Review

- [x] 4.1 Add module docstring to `adapters/clinical.py` explaining boundary validation strategy
- [x] 4.2 Add inline comments at remaining `ensure_json_*` sites documenting API version assumptions
- [x] 4.3 Update `ingestion/utils.py` docstrings to clarify usage guidelines
- [x] 4.4 Run full test suite to confirm no regressions
- [x] 4.5 Document reduction metrics (46→≤15 calls) in PR description
