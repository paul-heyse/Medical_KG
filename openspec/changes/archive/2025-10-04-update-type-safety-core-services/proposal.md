## Why

Residual TODOs track untyped core services (config manager, ingestion adapters, KG writer, retrieval API). These modules still require `Any` fallbacks, leaving `add-type-safety` incomplete and blocking full strict mypy adoption.

## What Changes

- Annotate core service modules (config, ingestion, retrieval, KG writer) and remove lingering `Any` dependencies
- Introduce TypedDicts/Protocols for ingestion payloads and external service responses
- Harden optional dependency facades so runtime fallbacks remain typed

## Impact

- Affected specs: `type-safety`
- Affected code: `src/Medical_KG/config`, `src/Medical_KG/ingestion`, `src/Medical_KG/retrieval`, `src/Medical_KG/kg`
