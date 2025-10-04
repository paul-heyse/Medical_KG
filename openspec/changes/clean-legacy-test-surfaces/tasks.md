# Tasks: Clean Legacy Test Surfaces

## 1. Audit Legacy Test Coverage

- [ ] 1.1 Identify all tests referencing "legacy" in names/comments
- [ ] 1.2 List fixture files for deprecated features
- [ ] 1.3 Find tests for removed API methods
- [ ] 1.4 Document tests that will break after legacy removal
- [ ] 1.5 Review test coverage reports for legacy code
- [ ] 1.6 Create removal plan prioritized by impact

## 2. Remove Legacy Pipeline Tests

- [ ] 2.1 Delete `test_run_async_legacy*` functions
- [ ] 2.2 Remove legacy consumption mode fixtures
- [ ] 2.3 Delete deprecation warning tests
- [ ] 2.4 Remove legacy wrapper integration tests
- [ ] 2.5 Clean up legacy-specific mocks
- [ ] 2.6 Update remaining pipeline tests
- [ ] 2.7 Verify pipeline test coverage maintained

## 3. Remove Legacy Ledger Tests

- [ ] 3.1 Delete string state coercion tests
- [ ] 3.2 Remove `LedgerState.LEGACY` test cases
- [ ] 3.3 Delete migration script tests
- [ ] 3.4 Remove string-to-enum mapping tests
- [ ] 3.5 Clean up legacy ledger fixtures
- [ ] 3.6 Update ledger test documentation
- [ ] 3.7 Verify ledger test coverage maintained

## 4. Remove Legacy Config Tests

- [ ] 4.1 Delete `LegacyValidator` test suite
- [ ] 4.2 Remove validator parity assertion tests
- [ ] 4.3 Delete legacy config file fixtures
- [ ] 4.4 Remove custom validation helper tests
- [ ] 4.5 Clean up legacy config schemas
- [ ] 4.6 Update config test documentation
- [ ] 4.7 Verify config test coverage maintained

## 5. Remove Legacy IR Tests

- [ ] 5.1 Delete untyped payload tests
- [ ] 5.2 Remove fallback coercion tests
- [ ] 5.3 Delete optional raw payload tests
- [ ] 5.4 Remove placeholder synthesis tests
- [ ] 5.5 Clean up untyped IR fixtures
- [ ] 5.6 Update IR test documentation
- [ ] 5.7 Verify IR test coverage maintained

## 6. Remove Legacy HTTP Client Tests

- [ ] 6.1 Delete `_NoopMetric` tests
- [ ] 6.2 Remove implicit detection tests
- [ ] 6.3 Delete placeholder metric integration tests
- [ ] 6.4 Remove auto-Prometheus registration tests
- [ ] 6.5 Clean up legacy telemetry fixtures
- [ ] 6.6 Update HTTP client test documentation
- [ ] 6.7 Verify HTTP client test coverage maintained

## 7. Remove Legacy CLI Tests

- [ ] 7.1 Delete legacy CLI command tests
- [ ] 7.2 Remove migration script tests
- [ ] 7.3 Delete legacy CLI fixture files
- [ ] 7.4 Remove command comparison tests
- [ ] 7.5 Clean up legacy CLI mocks
- [ ] 7.6 Update CLI test documentation
- [ ] 7.7 Verify CLI test coverage maintained

## 8. Delete Legacy Test Fixtures

- [ ] 8.1 Remove `legacy-ledger.jsonl` files
- [ ] 8.2 Delete legacy config YAML files
- [ ] 8.3 Remove untyped payload fixtures
- [ ] 8.4 Delete deprecated command fixtures
- [ ] 8.5 Clean up legacy test data directories
- [ ] 8.6 Update fixture README if present
- [ ] 8.7 Verify no broken fixture references

## 9. Remove Legacy Test Helpers

- [ ] 9.1 Delete legacy fixture generators
- [ ] 9.2 Remove deprecated mock factories
- [ ] 9.3 Delete legacy assertion helpers
- [ ] 9.4 Remove compatibility test utilities
- [ ] 9.5 Clean up unused test constants
- [ ] 9.6 Update test helper documentation
- [ ] 9.7 Verify no broken helper references

## 10. Add Replacement Smoke Tests

- [ ] 10.1 Add streaming pipeline smoke test
- [ ] 10.2 Add enum-only ledger smoke test
- [ ] 10.3 Add jsonschema validation smoke test
- [ ] 10.4 Add typed IR builder smoke test
- [ ] 10.5 Add normalized telemetry smoke test
- [ ] 10.6 Add unified CLI smoke test
- [ ] 10.7 Verify all smoke tests pass

## 11. Update Test Documentation

- [ ] 11.1 Remove legacy test pattern documentation
- [ ] 11.2 Update test writing guidelines
- [ ] 11.3 Document current testing patterns
- [ ] 11.4 Update test fixture generation guide
- [ ] 11.5 Refresh test coverage goals
- [ ] 11.6 Update CI/CD test documentation
- [ ] 11.7 Add test suite architecture overview

## 12. Optimize Test Suite

- [ ] 12.1 Consolidate redundant test cases
- [ ] 12.2 Optimize slow-running tests
- [ ] 12.3 Parallelize test execution where possible
- [ ] 12.4 Remove unnecessary test setup/teardown
- [ ] 12.5 Benchmark test suite execution time
- [ ] 12.6 Document test suite optimizations
- [ ] 12.7 Set performance regression baselines

## 13. Update CI Configuration

- [ ] 13.1 Remove legacy test job definitions
- [ ] 13.2 Update test matrix to reflect current code
- [ ] 13.3 Optimize CI test execution
- [ ] 13.4 Update coverage reporting configuration
- [ ] 13.5 Remove deprecated test environments
- [ ] 13.6 Update CI documentation
- [ ] 13.7 Verify CI runs efficiently

## 14. Validation

- [ ] 14.1 Run full test suite - all tests pass
- [ ] 14.2 Verify test coverage ≥ previous level
- [ ] 14.3 Check for any orphaned test files
- [ ] 14.4 Verify no broken test imports
- [ ] 14.5 Benchmark CI execution time improvement
- [ ] 14.6 Review test coverage report
- [ ] 14.7 Document test suite cleanup results

## 15. Communication and Documentation

- [ ] 15.1 Update testing documentation
- [ ] 15.2 Document test suite improvements
- [ ] 15.3 Update contributor testing guide
- [ ] 15.4 Add removal notice to CHANGELOG.md
- [ ] 15.5 Update test coverage badges if applicable
- [ ] 15.6 Communicate test suite changes to team
- [ ] 15.7 Archive old test documentation
