## Why

Retrieval services still rely on partially typed structures: cache entries remain untyped dictionaries, API response DTOs leak `Any`, and fusion/adjudication helpers avoid enforcing shape contracts. These gaps make the strict mypy configuration brittle when downstream modules adopt typed protocols.

## What Changes

- Add strong typing to `src/Medical_KG/retrieval` service, cache, and fusion utilities (TypedDicts, Protocols, generic helper functions)
- Update retrieval API models/routes to ensure request/response payloads and dependency injections are strictly typed
- Introduce typed interfaces for retrieval adapters (intent classifier, neighbor merger, ontology expander, caching) covering async and sync behaviors
- Extend optional dependency shims/tests to maintain strict typing for httpx/redis/backing stores used by retrieval
- Refresh integration tests to validate typed responses and catch regressions

## Impact

- Affected specs: retrieval service API and supporting infrastructure
- Affected code: `src/Medical_KG/retrieval/**`, `tests/retrieval/**`, related API bindings and optional dependency utilities
