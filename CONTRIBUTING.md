# Contributing

Thanks for supporting the Medical KG project! To keep the codebase healthy and fully typed,
please follow the steps below before sending a pull request.

## Checklist

1. **Create typed modules** – every new function, method, and class MUST include type
   annotations. Avoid `Any` unless interfacing with third-party libraries and prefer the
   typed facades in [`Medical_KG.compat`](./src/Medical_KG/compat/).
2. **Handle optional dependencies via compat** – use helpers such as `create_async_client`,
   `load_pipeline`, `load_encoding`, and `load_locust` so strict mypy checks work even when
   optional packages are missing locally.
3. **Standardise new extras** – when introducing a feature that depends on an optional
   package, update `DEPENDENCY_REGISTRY` (and tests) in
   [`Medical_KG.utils.optional_dependencies`](./src/Medical_KG/utils/optional_dependencies.py),
   add the extras group in `pyproject.toml`, refresh `docs/dependencies.md`, and provide a
   stub under `stubs/` so `mypy --strict` continues to pass.
4. **Run quality gates**:
   - `ruff check src tests`
   - `mypy --strict src/Medical_KG`
   - `pytest -q`
5. **Enforce IR type safety** – when modifying `src/Medical_KG/ir/`, run
   `mypy --strict src/Medical_KG/ir` and ensure `DocumentIR.metadata` retains
   the `payload_family`/`payload_type` contract. The IR module is linted with
   `ANN401`, so avoid introducing `Any` values outside of sanctioned
   compatibility shims.
6. **Update docs** – if you add new patterns or optional integrations, document the
   approach in [`docs/type_safety.md`](./docs/type_safety.md) and reference the unified
   ingestion CLI (`med ingest <adapter>`) for examples. All ingestion code should consume
   `IngestionPipeline.stream_events()` (or the eager `run_async()` helper); the deprecated
   `run_async_legacy()` wrapper was removed in October 2025. Historical migration material lives
   under [`docs/archive/cli_unification/`](./docs/archive/cli_unification/).

## Coding Standards

- Keep functions under ~50 lines and extract helpers rather than using `# type: ignore`.
- Prefer `Annotated` fields with `pydantic.Field` over assigning `Field` to typed
  attributes directly.
- Use Protocols or TypedDicts for structured payloads instead of plain dictionaries.
- Avoid monkeypatching `sys.path`; use `importlib` and typed factories for dynamic imports.

Adhering to these conventions ensures `mypy --strict` remains green and that optional
runtime dependencies do not leak `Any` types back into the application.
