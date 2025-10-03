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
