## Why
Ingestion adapters, catalog loaders, IR validators, and related utilities account for 41 strict mypy errors (plus 24 in facets, 22 in catalog, 14 in retrieval). These modules form the ingestion-to-index pipeline; without strong typing they violate the `type-safety` capability and risk runtime mismatches.

## What Changes
- Annotate ingestion adapter base classes and concrete implementations (clinical, literature, guideline) with precise async iterator signatures.
- Tighten catalog loaders, pipeline, and normalization code to operate on typed `Concept` models and mapping structures.
- Add stubs/helpers for jsonschema, OpenSearch, and other third-party APIs used during ingestion.
- Propagate typing through facets/retrieval utilities that consume ingestion outputs.

## Impact
- Affected specs: `type-safety`
- Affected code: `src/Medical_KG/ingestion/*`, `src/Medical_KG/catalog/*`, `src/Medical_KG/facets/*`, `src/Medical_KG/retrieval/*`, `src/Medical_KG/config/*`, `src/Medical_KG/ir/*`, `src/Medical_KG/embeddings/*`, `src/Medical_KG/security/*` (type-adjacent portions).
- Risks: broad surface area; mitigate via incremental module-by-module rollout and regression tests per adapter.
