# Add AsyncHttpClient Context Manager Support

## Why

`AsyncHttpClient` manages `AsyncClientProtocol` lifetime manually, requiring callers to remember to call `aclose()` to release network resources. This leads to:

- **Resource leaks** in tests that forget to clean up
- **Verbose boilerplate** in adapters (`try/finally` blocks)
- **Easy-to-miss cleanup** in error paths
- **Inconsistent patterns** across the codebase

Example of current pattern:
```python
client = AsyncHttpClient()
try:
    data = await client.get_json(url)
finally:
    await client.aclose()  # Easy to forget!
```

Adding `__aenter__/__aexit__` support enables:
```python
async with AsyncHttpClient() as client:
    data = await client.get_json(url)
    # Automatic cleanup!
```

This is a standard Python idiom for resource management and prevents resource leaks.

## What Changes

### Add Async Context Manager Protocol
- Implement `__aenter__` method (returns self)
- Implement `__aexit__` method (calls `aclose()`)
- Update `AsyncHttpClient` to support `async with` statement

### Update Adapters and Tests
- Refactor adapters to use context manager pattern
- Update tests to use `async with AsyncHttpClient(...)`
- Remove manual `aclose()` calls
- Simplify try/finally blocks

### Add Synchronous Wrapper (Optional)
- Create `HttpClientContext` synchronous context manager
- Wraps AsyncHttpClient for sync code using `asyncio.run()`
- Useful for CLI tools and synchronous test fixtures

### Documentation
- Update HTTP client docs with context manager examples
- Add migration guide for adapters
- Document when to use async with vs manual lifecycle

## Impact

- **Affected specs**: None (implementation detail)
- **Affected code**:
  - `src/Medical_KG/ingestion/http_client.py` (+15 lines for `__aenter__/__aexit__`)
  - `src/Medical_KG/ingestion/adapters/*.py` (update ~15 adapters)
  - `tests/ingestion/*.py` (update ~30 test files)
  - `docs/ingestion_runbooks.md` (+20 lines for context manager patterns)
- **Benefits**:
  - **Resource safety**: Guaranteed cleanup even on exceptions
  - **Cleaner code**: Less boilerplate in adapters and tests
  - **Standard pattern**: Pythonic resource management
  - **Fewer bugs**: Impossible to forget cleanup
- **Risk**: Low - backward compatible (old patterns still work)

