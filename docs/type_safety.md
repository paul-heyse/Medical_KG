# Type Safety Guidelines (Work-in-Progress)

## Suppression Audit
- `# type: ignore`: none in repository after removing legacy patch artifacts.
- mypy config: `strict = true`, no `exclude` or `ignore_missing_imports` entries.

## Optional Dependency Facades

- `Medical_KG.utils.optional_dependencies` now exposes Protocol-backed helpers for:
  - token counting (tiktoken encodings)
  - spaCy language pipelines
  - torch CUDA enforcement
  - Prometheus gauges, counters, and histograms used by metrics exporters
  - HTTPX clients, responses, transports, and ASGI adapters
  - Locust `HttpUser`, `between`, and `task` helpers
- Downstream modules import these helpers instead of performing ad-hoc optional imports. Example:

```python
from Medical_KG.utils.optional_dependencies import get_httpx_module

HTTPX = get_httpx_module()

async with HTTPX.AsyncClient(transport=HTTPX.ASGITransport(app=app), base_url="http://test") as client:
    response = await client.post("/facets/generate", json={"chunk_ids": ["chunk-1"]})
    response.raise_for_status()
```

- When the dependency is absent the helper either returns `None` (for optional features like spaCy) or raises a descriptive `ModuleNotFoundError` (for tooling that must be explicitly installed such as Locust and HTTPX).

## Typed Tests and Fixtures

- All fixtures in `tests/ingestion/`, `tests/config/test_cli.py`, and `tests/test_retrieval_service.py` now declare explicit return types to satisfy `mypy --strict`.
- Async helper utilities (e.g., `_run` wrappers) accept `Awaitable[T]` and return `T`, preventing leakage of `Any` from coroutine scheduling helpers.
- Test doubles for optional dependencies (HTTPX transports, Locust users) rely on the shared Protocols exported by `optional_dependencies` so strict type checking succeeds without local stub modules.

## JSON Payload Typing
- Added `Medical_KG.types.json` as the shared source of JSON-compatible type aliases
  (`JSONValue`, `JSONObject`, etc.) so config and ingestion modules no longer fall
  back to ``Any`` when manipulating nested dictionaries.
- `ConfigManager` now consumes these aliases, guaranteeing that deep merges,
  environment overrides, and placeholder resolution work entirely on typed
  payloads.

## Core Service Configurations
- `Medical_KG.config.models` exposes dataclasses for auth settings and the PDF
  pipeline, providing strongly typed accessors for downstream services.
- CLI entrypoints consume the new `PdfPipelineSettings`, eliminating the
  previous `dict` indexing and ensuring path handling stays typed end-to-end.
- `ConfigManager.validate_jwt` validates tokens against the typed
  `AuthSettings`, removing dictionary lookups and stringly-typed scope checks.

Further sections will be completed alongside implementation.
