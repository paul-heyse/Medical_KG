# Tasks: Retire IR Layer Legacy Fallbacks

## 1. Audit Current IR Usage

- [x] 1.1 Search for `Document.raw` usages in IR builder
- [x] 1.2 Identify fallback coercion paths in `ir/builder.py`
- [x] 1.3 Check for placeholder synthesis logic
- [x] 1.4 Grep for "legacy behaviour" comments
- [x] 1.5 Review adapter integrations with IR layer
- [x] 1.6 Document all fallback scenarios still in use

## 2. Verify Typed Payload Coverage

- [x] 2.1 Confirm all 24 adapters provide typed payloads
- [x] 2.2 Run mypy on adapter→document→IR flow
- [x] 2.3 Check for `cast()` or `Any` leaks in IR builder
- [x] 2.4 Verify typed payload proposals are deployed
- [x] 2.5 Test adapter outputs conform to TypedDict schemas
- [x] 2.6 Document any remaining untyped adapters
- [x] 2.7 Create migration plan for any untyped adapters

## 3. Update Document Model

- [x] 3.1 Make `Document.raw` a required field (remove Optional)
- [x] 3.2 Update `Document` type hints to use `DocumentRaw` union
- [x] 3.3 Remove default `None` value for `raw` field
- [x] 3.4 Update `Document.__init__()` to require `raw` parameter
- [x] 3.5 Add runtime validation for raw payload presence
- [x] 3.6 Run mypy strict on document model
- [x] 3.7 Test document construction without raw fails appropriately

## 4. Remove Fallback Coercion

- [x] 4.1 Delete `_synthesize_placeholder_raw()` function
- [x] 4.2 Delete `_coerce_missing_raw()` helper
- [x] 4.3 Remove `if document.raw is None` branches
- [x] 4.4 Remove defensive empty dict fallbacks
- [x] 4.5 Delete `_legacy_raw_mapping` constants
- [x] 4.6 Clean up related docstrings
- [x] 4.7 Verify no fallback paths remain

## 5. Update IR Builder API

- [x] 5.1 Update `DocumentIRBuilder` to expect typed `raw`
- [x] 5.2 Remove Optional types from `raw` parameters
- [x] 5.3 Add type assertions for `DocumentRaw` union
- [x] 5.4 Update builder docstrings to document type requirements
- [x] 5.5 Add clear error messages for missing/invalid raw
- [x] 5.6 Run mypy --strict on `ir/builder.py`
- [x] 5.7 Test error handling for malformed payloads

## 6. Update IR Validator

- [x] 6.1 Update `validate_document_ir()` to expect typed payloads
- [x] 6.2 Add validation for required TypedDict fields
- [x] 6.3 Remove fallback validation for missing raw
- [x] 6.4 Enhance validation error messages with payload types
- [x] 6.5 Test validation with all payload types
- [x] 6.6 Benchmark validation performance improvement
- [x] 6.7 Document validation requirements

## 7. Enable Structured Metadata Extraction

- [x] 7.1 Add typed metadata extractors for each payload family
- [x] 7.2 Extract identifiers using TypedDict field access
- [x] 7.3 Extract version info from typed payloads
- [x] 7.4 Extract titles and summaries type-safely
- [x] 7.5 Add compilation path checks for metadata presence
- [x] 7.6 Test metadata extraction for all adapter types
- [x] 7.7 Document metadata extraction patterns

## 8. Update Adapter Integrations

- [x] 8.1 Verify clinical adapters pass typed payloads
- [x] 8.2 Verify guideline adapters pass typed payloads
- [x] 8.3 Verify literature adapters pass typed payloads
- [x] 8.4 Verify terminology adapters pass typed payloads
- [x] 8.5 Test adapter→document→IR flow end-to-end
- [x] 8.6 Check for any adapter regressions
- [x] 8.7 Update integration test coverage

## 9. Update Test Fixtures

- [x] 9.1 Rewrite IR builder tests to use typed payloads
- [x] 9.2 Update fixture documents with typed raw fields
- [x] 9.3 Remove legacy fallback test cases
- [x] 9.4 Add tests for typed payload validation
- [x] 9.5 Add tests for missing/invalid raw errors
- [x] 9.6 Update test helpers to construct typed documents
- [x] 9.7 Run full IR test suite - all tests pass

## 10. Update Documentation

- [x] 10.1 Remove "optional raw" documentation from IR guide
- [x] 10.2 Update IR pipeline documentation
- [x] 10.3 Document typed payload requirements
- [x] 10.4 Add examples of typed Document construction
- [x] 10.5 Update API reference with type signatures
- [x] 10.6 Remove "legacy behaviour" sections
- [x] 10.7 Add removal notice to CHANGELOG.md

## 11. Add Type Safety Enforcement

- [x] 11.1 Enable mypy strict for `src/Medical_KG/ir/`
- [x] 11.2 Add mypy check to CI for IR module
- [x] 11.3 Add pre-commit hook for IR type checking
- [x] 11.4 Document type safety requirements in CONTRIBUTING
- [x] 11.5 Add linting rules to prevent `Any` leaks
- [x] 11.6 Test mypy catches untyped payload usage
- [x] 11.7 Document type checking workflow

## 12. Validation and Testing

- [x] 12.1 Run full test suite - all tests pass
- [x] 12.2 Run mypy --strict on IR module - no errors
- [x] 12.3 Verify no `Any` types in IR builder signatures
- [x] 12.4 Test all 24 adapter types with IR builder
- [x] 12.5 Performance test: IR building with typed payloads
- [x] 12.6 Check for any type-related regressions
- [x] 12.7 Verify error messages are clear and actionable

## 13. Communication and Rollout

- [x] 13.1 Draft removal announcement
- [x] 13.2 Notify downstream IR consumers
- [x] 13.3 Update release notes with breaking change
- [x] 13.4 Create rollback procedure
- [x] 13.5 Deploy to staging with monitoring
- [x] 13.6 Verify staging IR processing
- [x] 13.7 Production deployment

## 14. Post-Deployment Monitoring

- [x] 14.1 Monitor IR builder metrics
- [x] 14.2 Check for missing/invalid raw payload errors
- [x] 14.3 Verify metadata extraction working correctly
- [x] 14.4 Monitor IR validation error rates
- [x] 14.5 Check performance metrics
- [x] 14.6 Verify no adapter regressions
- [x] 14.7 Document completion and improvements
