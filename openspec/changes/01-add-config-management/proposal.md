# Add Configuration Management

## Why

Centralized, validated configuration enables runtime behavior control without code changes, supports multi-environment deployments (dev/staging/prod), and allows hot-reload for non-breaking changes. Schema validation prevents misconfigurations; overrides support experimentation.

## What Changes

- Define master config.yaml (single source of truth; sections: sources, chunking, embeddings, retrieval, extraction, kg, catalog, apis, observability, licensing)
- Create config.schema.json (JSON Schema validation for all fields)
- Implement hierarchical overrides (env vars > config-override.yaml > config.yaml)
- Add hot-reload support (POST /admin/reload with signed JWT; validate + apply without restart)
- Implement feature flags (toggle SPLADE, reranker, experimental extractors)
- Add licensing config (policy.yaml: SNOMED/UMLS/MedDRA flags + territories)
- Create config validation CLI (med config validate --strict)
- Implement config versioning (track config_version; emit as metric)

## Impact

- **Affected specs**: NEW `config-management` capability
- **Affected code**: NEW `/config/`, config.yaml, config.schema.json, policy.yaml
- **Dependencies**: All services read config on startup + reload signal
- **Downstream**: Ops can tune retrieval weights, chunking profiles, rate limits without redeploying
