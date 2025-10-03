# Implementation Tasks

## 1. Implement Context Manager Protocol

- [x] 1.1 Add `__aenter__` method to `AsyncHttpClient` (returns self)
- [x] 1.2 Add `__aexit__` method to `AsyncHttpClient` (calls `aclose()`)
- [x] 1.3 Ensure proper exception handling in `__aexit__`
- [x] 1.4 Add type hints for context manager protocol
- [x] 1.5 Test context manager with exceptions (cleanup still happens)

## 2. Update Core Tests

- [x] 2.1 Add test for `async with AsyncHttpClient()` basic usage
- [x] 2.2 Add test verifying cleanup happens on success
- [x] 2.3 Add test verifying cleanup happens on exception
- [x] 2.4 Add test for nested context managers
- [x] 2.5 Verify existing manual `aclose()` patterns still work

## 3. Refactor Ingestion Adapters

- [ ] 3.1 Update `BaseAdapter` to use context manager in examples
- [ ] 3.2 Refactor terminology adapters (MeSH, UMLS, LOINC, ICD-11, SNOMED)
- [ ] 3.3 Refactor literature adapters (PubMed, PMC, MedRxiv)
- [ ] 3.4 Refactor clinical adapters (ClinicalTrials, openFDA, DailyMed, RxNorm)
- [ ] 3.5 Refactor guideline adapters (NICE, USPSTF, CDC, WHO)
- [ ] 3.6 Verify all adapters pass tests after refactoring

## 4. Refactor Test Suite

- [x] 4.1 Update `conftest.py` fixtures to use context managers
- [x] 4.2 Refactor adapter tests to use `async with`
- [x] 4.3 Refactor HTTP client tests
- [x] 4.4 Remove manual `aclose()` calls from tests
- [x] 4.5 Simplify test cleanup logic

## 5. Optional: Add Synchronous Wrapper

- [ ] 5.1 Create `HttpClientContext` synchronous context manager class
- [ ] 5.2 Implement `__enter__` and `__exit__` using `asyncio.run()`
- [ ] 5.3 Add tests for synchronous wrapper
- [ ] 5.4 Document when to use sync vs async context managers

## 6. Documentation

- [ ] 6.1 Update `http_client.py` module docstring with context manager examples
- [ ] 6.2 Add context manager section to ingestion runbooks
- [ ] 6.3 Create migration guide from manual cleanup to context managers
- [ ] 6.4 Update adapter creation guide with context manager pattern
- [ ] 6.5 Add troubleshooting for common context manager mistakes

## 7. Validation

- [ ] 7.1 Run full test suite - all tests pass
- [ ] 7.2 Verify no resource leaks using memory profiler
- [ ] 7.3 Test with real API calls (ensure cleanup works)
- [x] 7.4 Run mypy --strict - no type errors
- [ ] 7.5 Verify backward compatibility (old patterns still work)

