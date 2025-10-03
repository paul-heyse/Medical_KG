## Why
Strict mypy runs surface 73 errors across the extraction stack (models, services, metrics, KG writers), blocking the `type-safety` capability from meeting the "Strict Type Checking" requirement.

## What Changes
- Annotate extraction dataclasses, Pydantic-like models, and service entry points.
- Refactor shared extraction base classes to expose typed accessors instead of dynamic attributes.
- Tighten KG writer payloads and metrics aggregation to operate on typed collections.
- Provide typed helper interfaces for downstream consumers (briefing, API) that ingest extraction results.

## Impact
- Affected specs: `type-safety`
- Affected code: `src/Medical_KG/extraction/*`, `src/Medical_KG/briefing/*`, `src/Medical_KG/catalog/*` (type-facing portions), `tests/extraction/*`
- Risks: touching serialization models may reveal hidden schema drift; mitigation via expanded unit tests and smoke tests.
