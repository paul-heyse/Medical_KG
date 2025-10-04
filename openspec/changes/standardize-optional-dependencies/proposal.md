# Standardize Optional Dependency Handling

## Why

Current optional dependency handling is inconsistent:

- Generic `ModuleNotFoundError` with no context
- Wide mypy `ignore_errors` suppressions hide type drift
- No clear guidance on which extras to install
- Contributors get cryptic import errors
- Optional features require bespoke troubleshooting

From `repo_optimization_opportunities.md`: "Optional dependency helpers currently raise generic `ModuleNotFoundError` messages and the project silences mypy across wide swaths of the codebase. This invites one-off fixes every time dependencies move."

## What Changes

- Introduce `MissingDependencyError` with feature name and install hint
- Replace all `ModuleNotFoundError` with structured errors
- Add protocol shims for optional packages
- Incrementally reduce mypy `ignore_errors` lists by 50%+
- Document dependency matrix in developer guide
- Add extras group mapping (observability → prometheus, opentelemetry)

## Impact

- **Affected code**: `src/Medical_KG/utils/optional_dependencies.py`, all optional imports
- **Benefits**: Better contributor UX, earlier CI signal, plug-and-play features
- **Breaking changes**: None (error messages improve but still raise on missing deps)
- **Risk**: Low - pure refactoring with backwards compatibility
