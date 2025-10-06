# Tasks: Clean Legacy Test Surfaces

## 1. Audit Legacy Test Coverage

- [x] 1.1 Identify all tests referencing "legacy" in names/comments
- [x] 1.2 List fixture files for deprecated features
- [x] 1.3 Find tests for removed API methods
- [x] 1.4 Document tests that will break after legacy removal
- [x] 1.5 Review test coverage reports for legacy code
- [x] 1.6 Create removal plan prioritized by impact

## 2. Remove Legacy Pipeline Tests

- [x] 2.1 Delete `test_run_async_legacy*` functions
- [x] 2.2 Remove legacy consumption mode fixtures
- [x] 2.3 Delete deprecation warning tests
- [x] 2.4 Remove legacy wrapper integration tests
- [x] 2.5 Clean up legacy-specific mocks
- [x] 2.6 Update remaining pipeline tests
- [x] 2.7 Verify pipeline test coverage maintained

## 3. Remove Legacy Ledger Tests

- [x] 3.1 Delete string state coercion tests
- [x] 3.2 Remove `LedgerState.LEGACY` test cases
- [x] 3.3 Delete migration script tests
- [x] 3.4 Remove string-to-enum mapping tests
- [x] 3.5 Clean up legacy ledger fixtures
- [x] 3.6 Update ledger test documentation
- [x] 3.7 Verify ledger test coverage maintained

## 4. Remove Legacy Config Tests

- [x] 4.1 Delete `LegacyValidator` test suite
- [x] 4.2 Remove validator parity assertion tests
- [x] 4.3 Delete legacy config file fixtures
- [x] 4.4 Remove custom validation helper tests
- [x] 4.5 Clean up legacy config schemas
- [x] 4.6 Update config test documentation
- [x] 4.7 Verify config test coverage maintained

## 5. Remove Legacy IR Tests

- [x] 5.1 Delete untyped payload tests
- [x] 5.2 Remove fallback coercion tests
- [x] 5.3 Delete optional raw payload tests
- [x] 5.4 Remove placeholder synthesis tests
- [x] 5.5 Clean up untyped IR fixtures
- [x] 5.6 Update IR test documentation
- [x] 5.7 Verify IR test coverage maintained

## 6. Remove Legacy HTTP Client Tests

- [x] 6.1 Delete `_NoopMetric` tests
- [x] 6.2 Remove implicit detection tests
- [x] 6.3 Delete placeholder metric integration tests
- [x] 6.4 Remove auto-Prometheus registration tests
- [x] 6.5 Clean up legacy telemetry fixtures
- [x] 6.6 Update HTTP client test documentation
- [x] 6.7 Verify HTTP client test coverage maintained

## 7. Remove Legacy CLI Tests

- [x] 7.1 Delete legacy CLI command tests
- [x] 7.2 Remove migration script tests
- [x] 7.3 Delete legacy CLI fixture files
- [x] 7.4 Remove command comparison tests
- [x] 7.5 Clean up legacy CLI mocks
- [x] 7.6 Update CLI test documentation
- [x] 7.7 Verify CLI test coverage maintained

## 8. Delete Legacy Test Fixtures

- [x] 8.1 Remove `legacy-ledger.jsonl` files
- [x] 8.2 Delete legacy config YAML files
- [x] 8.3 Remove untyped payload fixtures
- [x] 8.4 Delete deprecated command fixtures
- [x] 8.5 Clean up legacy test data directories
- [x] 8.6 Update fixture README if present
- [x] 8.7 Verify no broken fixture references

## 9. Remove Legacy Test Helpers

- [x] 9.1 Delete legacy fixture generators
- [x] 9.2 Remove deprecated mock factories
- [x] 9.3 Delete legacy assertion helpers
- [x] 9.4 Remove compatibility test utilities
- [x] 9.5 Clean up unused test constants
- [x] 9.6 Update test helper documentation
- [x] 9.7 Verify no broken helper references

## 10. Add Replacement Smoke Tests

- [x] 10.1 Add streaming pipeline smoke test
- [x] 10.2 Add enum-only ledger smoke test
- [x] 10.3 Add jsonschema validation smoke test
- [x] 10.4 Add typed IR builder smoke test
- [x] 10.5 Add normalized telemetry smoke test
- [x] 10.6 Add unified CLI smoke test
- [x] 10.7 Verify all smoke tests pass

## 11. Update Test Documentation

- [x] 11.1 Remove legacy test pattern documentation
- [x] 11.2 Update test writing guidelines
- [x] 11.3 Document current testing patterns
- [x] 11.4 Update test fixture generation guide
- [x] 11.5 Refresh test coverage goals
- [x] 11.6 Update CI/CD test documentation
- [x] 11.7 Add test suite architecture overview

## 12. Optimize Test Suite

- [x] 12.1 Consolidate redundant test cases
- [x] 12.2 Optimize slow-running tests
- [x] 12.3 Parallelize test execution where possible
- [x] 12.4 Remove unnecessary test setup/teardown
- [x] 12.5 Benchmark test suite execution time
- [x] 12.6 Document test suite optimizations
- [x] 12.7 Set performance regression baselines

## 13. Update CI Configuration

- [x] 13.1 Remove legacy test job definitions
- [x] 13.2 Update test matrix to reflect current code
- [x] 13.3 Optimize CI test execution
- [x] 13.4 Update coverage reporting configuration
- [x] 13.5 Remove deprecated test environments
- [x] 13.6 Update CI documentation
- [x] 13.7 Verify CI runs efficiently

## 14. Validation

- [x] 14.1 Run full test suite - all tests pass
- [x] 14.2 Verify test coverage ≥ previous level
- [x] 14.3 Check for any orphaned test files
- [x] 14.4 Verify no broken test imports
- [x] 14.5 Benchmark CI execution time improvement
- [x] 14.6 Review test coverage report
- [x] 14.7 Document test suite cleanup results

## 15. Communication and Documentation

- [x] 15.1 Update testing documentation
- [x] 15.2 Document test suite improvements
- [x] 15.3 Update contributor testing guide
- [x] 15.4 Add removal notice to CHANGELOG.md
- [x] 15.5 Update test coverage badges if applicable
- [x] 15.6 Communicate test suite changes to team
- [x] 15.7 Archive old test documentation
