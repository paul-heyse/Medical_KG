# Contributing Guidelines

## Type-Safe Optional Dependencies
- Import optional third-party packages through `Medical_KG.utils.optional_dependencies`.
  - Use `get_httpx_module()` for HTTPX clients and transports.
  - Use `load_locust()` for Locust load tests.
  - Use `build_counter`/`build_histogram` when exporting Prometheus metrics.
- Avoid direct `try/except ImportError` blocks in modules—extend the shared helper instead.

## Tests & Fixtures
- Annotate pytest fixtures and async helpers with explicit types. Reuse the shared `_run` helper pattern from `tests/ingestion/test_adapters.py` when driving async adapters.
- When mocking optional dependencies (HTTPX transports, Locust users), rely on the Protocols returned by `optional_dependencies` so `mypy --strict` passes without local stubs.
- Run `PYTHONPATH=src python -m mypy --strict tests/...` for touched directories and ensure the coverage hook (`pytest -q`) continues to meet the 95% requirement.

## Pull Request Checklist
- Include documentation updates in `docs/type_safety.md` when introducing new patterns.
- Regenerate or capture OpenAPI diffs if API routes change.
- Update relevant OpenSpec task checklists after completing staged work.
