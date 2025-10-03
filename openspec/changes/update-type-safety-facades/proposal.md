## Why

Optional dependency facades (torch, locust, httpx test clients) still leak `Any` types, and several test fixtures remain untyped. These gaps block completion of `add-type-safety` tasks for optional dependencies and typed fixtures.

## What Changes

- Formalize Protocol-based facades for optional libraries and ensure runtime fallbacks remain typed
- Annotate test fixtures/mocks, especially for CLI and async transports
- Update documentation/contributing guides with new typed examples

## Impact

- Affected specs: `type-safety`
- Affected code: `src/Medical_KG/utils/optional_dependencies.py`, test fixtures under `tests/`, documentation
