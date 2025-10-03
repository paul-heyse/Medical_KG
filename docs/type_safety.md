# Type Safety Guidelines (Work-in-Progress)

## Suppression Audit
- `# type: ignore`: none in repository after removing legacy patch artifacts.
- mypy config: `strict = true`, no `exclude` or `ignore_missing_imports` entries.

## Untyped Optional Dependencies
- `Medical_KG.utils.optional_dependencies` now exposes Protocol-backed helpers for:
  - token counting (tiktoken encodings)
  - spaCy language pipelines
  - torch CUDA enforcement
  - Prometheus gauges used by config manager
- Downstream modules import these helpers instead of performing ad-hoc optional imports.
- Remaining modules with optional bindings: `embeddings.monitoring`, `embeddings.splade`, `pdf.minеру` (pending migration onto the helper module).

Further sections will be completed alongside implementation.
