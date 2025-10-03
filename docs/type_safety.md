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

Further sections will be completed alongside implementation.
