## Why
Despite recent reductions in `# type: ignore` usage, the codebase still contains loosely typed modules, optional dependencies without stubs, and untyped tests. Mypy currently reports hundreds of errors, forcing us to exclude directories and suppress checks. Without a dedicated type safety initiative, regressions will continue slipping through and contributors will reintroduce suppressions.

## What Changes
- Audit all remaining mypy exclusions (`exclude`, `ignore_missing_imports`, `# type: ignore`) and eliminate them by providing precise annotations or typed shims.
- Introduce typed wrappers for optional dependencies (e.g., httpx, locust, torch, tiktoken) using runtime detection + Protocols where needed.
- Expand our pydantic shim to cover Annotated, UnionType, and length checks without ignores.
- Type critical adapters, formatters, CLI utilities, and tests to ensure payloads are treated as `Mapping`/`Sequence` rather than `Any`.
- Configure mypy in strict mode for all `src/Medical_KG` modules and targeted `tests/` folders, adding enforcement to CI.
- Provide contributor guidance on adding annotations, using Protocols, and handling optional imports.

## Impact
- **Specs**: adds a `type-safety` capability describing coverage thresholds, no-suppression policy, and CI enforcement.
- **Code**: touches most modules to add annotations, typed helpers, Protocols, and runtime guards; updates tests to use typed fixtures.
- **Tooling**: updates mypy configuration (pyproject), possibly adds stub packages or vendored typing helpers.
- **Docs**: adds type-safety guidelines under `docs/`.
- **Risks**: broad surface area; mitigated via incremental PRs and high test coverage.
