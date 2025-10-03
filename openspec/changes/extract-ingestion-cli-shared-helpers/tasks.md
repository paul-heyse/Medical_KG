# Implementation Tasks

## 1. Analysis and Design

- [ ] 1.1 Audit `Medical_KG.cli` for ingestion-related functions
- [ ] 1.2 Audit `Medical_KG.ingestion.cli` for equivalent functions
- [ ] 1.3 Create comparison matrix (function pairs, differences)
- [ ] 1.4 Identify which implementation is "best" for each function
- [ ] 1.5 Design shared helper API (function signatures, types)
- [ ] 1.6 Document helper responsibilities and contracts

## 2. Create cli_helpers Module

- [ ] 2.1 Create `src/Medical_KG/ingestion/cli_helpers.py` module
- [ ] 2.2 Add comprehensive module docstring with usage examples
- [ ] 2.3 Define type aliases for common CLI types
- [ ] 2.4 Add module-level constants (error codes, defaults)

## 3. Extract NDJSON Loading Helper

- [ ] 3.1 Implement `load_ndjson_batch()` function
- [ ] 3.2 Include JSON validation (from modern CLI)
- [ ] 3.3 Handle malformed JSON with clear error messages
- [ ] 3.4 Support both file paths and file objects
- [ ] 3.5 Add progress callback for large files
- [ ] 3.6 Add comprehensive docstring and type hints

## 4. Extract Adapter Invocation Helper

- [ ] 4.1 Implement `invoke_adapter()` function
- [ ] 4.2 Handle adapter registry lookup
- [ ] 4.3 Manage adapter context and HTTP client lifecycle
- [ ] 4.4 Support custom adapter parameters
- [ ] 4.5 Add error handling for adapter failures
- [ ] 4.6 Add type hints for adapter protocol

## 5. Extract Error Formatting Helper

- [ ] 5.1 Implement `format_cli_error()` function
- [ ] 5.2 Consistent error message formatting
- [ ] 5.3 Include remediation hints where applicable
- [ ] 5.4 Support different error types (validation, runtime, network)
- [ ] 5.5 Add optional stack trace for debugging
- [ ] 5.6 Add color support (optional, detect TTY)

## 6. Extract Ledger Resume Helper

- [ ] 6.1 Implement `handle_ledger_resume()` function
- [ ] 6.2 Load ledger and determine resume point
- [ ] 6.3 Filter already-processed records
- [ ] 6.4 Return resume statistics (skipped, remaining)
- [ ] 6.5 Handle missing or corrupted ledger files
- [ ] 6.6 Add dry-run mode for resume preview

## 7. Extract Result Formatting Helper

- [ ] 7.1 Implement `format_results()` function
- [ ] 7.2 Support multiple output formats (text, JSON, table)
- [ ] 7.3 Include success/failure counts
- [ ] 7.4 Show timing and performance metrics
- [ ] 7.5 Add optional verbose mode
- [ ] 7.6 Ensure format is parseable by CI scripts

## 8. Add Unit Tests for Helpers

- [ ] 8.1 Test `load_ndjson_batch()` with valid files
- [ ] 8.2 Test `load_ndjson_batch()` with malformed JSON
- [ ] 8.3 Test `load_ndjson_batch()` with empty files
- [ ] 8.4 Test `invoke_adapter()` with valid adapters
- [ ] 8.5 Test `invoke_adapter()` with invalid adapter names
- [ ] 8.6 Test `format_cli_error()` with different error types
- [ ] 8.7 Test `handle_ledger_resume()` with existing ledger
- [ ] 8.8 Test `handle_ledger_resume()` with no ledger
- [ ] 8.9 Test `format_results()` with different formats
- [ ] 8.10 Test edge cases (large files, Unicode, special chars)

## 9. Refactor Legacy CLI

- [ ] 9.1 Update `Medical_KG.cli` imports to use helpers
- [ ] 9.2 Replace NDJSON loading with `load_ndjson_batch()`
- [ ] 9.3 Replace adapter invocation with `invoke_adapter()`
- [ ] 9.4 Replace error formatting with `format_cli_error()`
- [ ] 9.5 Replace result formatting with `format_results()`
- [ ] 9.6 Remove duplicated code
- [ ] 9.7 Add integration test verifying legacy CLI still works

## 10. Refactor Modern CLI

- [ ] 10.1 Update `Medical_KG.ingestion.cli` imports to use helpers
- [ ] 10.2 Replace NDJSON loading with `load_ndjson_batch()`
- [ ] 10.3 Replace adapter invocation with `invoke_adapter()`
- [ ] 10.4 Replace error formatting with `format_cli_error()`
- [ ] 10.5 Replace result formatting with `format_results()`
- [ ] 10.6 Remove duplicated code
- [ ] 10.7 Add integration test verifying modern CLI still works

## 11. Add Integration Tests

- [ ] 11.1 Test legacy CLI end-to-end with real adapters
- [ ] 11.2 Test modern CLI end-to-end with real adapters
- [ ] 11.3 Test resume functionality in both CLIs
- [ ] 11.4 Test error handling in both CLIs
- [ ] 11.5 Compare outputs from both CLIs (should match)
- [ ] 11.6 Test with production-like data

## 12. Documentation

- [ ] 12.1 Add docstrings to all helper functions
- [ ] 12.2 Create architecture diagram (CLIs → helpers → adapters)
- [ ] 12.3 Update `docs/ingestion_runbooks.md` with helper details
- [ ] 12.4 Add developer guide section for CLI helpers
- [ ] 12.5 Document extension points for future helpers
- [ ] 12.6 Add examples of using helpers in custom scripts

## 13. Code Review and Validation

- [ ] 13.1 Run full test suite - all tests pass
- [ ] 13.2 Run mypy --strict - no type errors
- [ ] 13.3 Run ruff check - no lint errors
- [ ] 13.4 Verify no breaking changes (CLI behavior identical)
- [ ] 13.5 Code review focusing on helper API design
- [ ] 13.6 Performance testing (ensure no regression)

## 14. Monitoring and Rollout

- [ ] 14.1 Add logging to helper functions
- [ ] 14.2 Add metrics for helper usage (optional)
- [ ] 14.3 Deploy to staging environment
- [ ] 14.4 Run smoke tests in staging
- [ ] 14.5 Monitor for regressions (error rates, performance)
- [ ] 14.6 Deploy to production after validation
