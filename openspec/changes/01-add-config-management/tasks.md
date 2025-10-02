# Implementation Tasks

## 1. Master config.yaml Structure

- [ ] 1.1 Define sources section (api_keys, rate_limits, retry_configs per source)
- [ ] 1.2 Define chunking section (profiles: IMRaD/Registry/SPL/Guideline with target_tokens, overlap, tau_coh)
- [ ] 1.3 Define embeddings section (vllm_api_base, batch_size, splade_top_k, require_gpu)
- [ ] 1.4 Define retrieval section (fusion weights, rrf_k, reranker enabled/topN, neighbor_merge min_cosine/max_tokens)
- [ ] 1.5 Define extraction section (per-extractor prompts, temperature, max_tokens, confidence_threshold)
- [ ] 1.6 Define kg section (neo4j_uri, batch_size, shacl_enabled)
- [ ] 1.7 Define catalog section (update schedules per ontology, license gates)
- [ ] 1.8 Define apis section (rate_limits per scope, auth config, cors origins)
- [ ] 1.9 Define observability section (log level, metrics push_interval, tracing sample_rate)
- [ ] 1.10 Define licensing section (pointer to policy.yaml)

## 2. config.schema.json

- [ ] 2.1 Define JSON Schema for all config sections
- [ ] 2.2 Add constraints (e.g., retrieval fusion weights must sum to 1.0; chunking target_tokens > 0)
- [ ] 2.3 Add enums (log_level: debug/info/warn/error; intent: pico/endpoint/ae/dose/eligibility/general)
- [ ] 2.4 Add descriptions for each field

## 3. policy.yaml (Licensing)

- [ ] 3.1 Define vocabs section (SNOMED{licensed, territory}, MedDRA{licensed}, LOINC{licensed}, RxNorm{licensed}, HPO{licensed})
- [ ] 3.2 Define actions section (redact_unlicensed_codes, block_kg_write_without_provenance)
- [ ] 3.3 Validate on startup (if vocab used but not licensed → fail or warn)

## 4. Hierarchical Overrides

- [ ] 4.1 Load config.yaml (base)
- [ ] 4.2 Overlay config-override.yaml if present (dev/test overrides)
- [ ] 4.3 Overlay env vars (e.g., VLLM_API_BASE, RETRIEVAL_FUSION_WEIGHTS)
- [ ] 4.4 Final config = base + overrides + env vars

## 5. Validation

- [ ] 5.1 Implement config validator (load YAML; validate against schema; check constraints)
- [ ] 5.2 Create CLI `med config validate --strict` (fail on any error/warning)
- [ ] 5.3 Run validation on startup (fail-fast if invalid)
- [ ] 5.4 Run validation before hot-reload (reject if invalid)

## 6. Hot-Reload

- [ ] 6.1 Implement POST /admin/reload endpoint (requires admin scope + signed JWT)
- [ ] 6.2 Re-read config files (config.yaml + config-override.yaml + env vars)
- [ ] 6.3 Validate new config
- [ ] 6.4 Apply non-breaking changes (e.g., retrieval weights, log level, rate limits) without restart
- [ ] 6.5 Reject breaking changes (e.g., vllm_api_base, neo4j_uri) with clear error
- [ ] 6.6 Increment config_version; emit metric

## 7. Feature Flags

- [ ] 7.1 Define feature_flags section in config (splade_enabled, reranker_enabled, extraction_experimental_enabled)
- [ ] 7.2 Check flags at runtime (if !splade_enabled → skip SPLADE retriever; adjust fusion weights)
- [ ] 7.3 Emit metrics with flag states (feature_flag{name, enabled})

## 8. Config Versioning

- [ ] 8.1 Compute config_hash (SHA256 of canonical YAML)
- [ ] 8.2 Store config_version (semantic version or timestamp + hash)
- [ ] 8.3 Emit config_version as metric (config_info{version, hash})
- [ ] 8.4 Log config_version on startup and after reload

## 9. Environment-Specific Configs

- [ ] 9.1 Create config-dev.yaml (local dev; mock APIs; verbose logging)
- [ ] 9.2 Create config-staging.yaml (staging; real APIs with test keys)
- [ ] 9.3 Create config-prod.yaml (production; secrets from Vault; strict licensing)
- [ ] 9.4 Use CONFIG_ENV env var to select environment

## 10. Secrets Management

- [ ] 10.1 Do NOT store secrets in config.yaml (use placeholders like ${UMLS_API_KEY})
- [ ] 10.2 Resolve placeholders from Vault/KMS at runtime
- [ ] 10.3 Mask secrets in logs and error messages

## 11. Testing

- [ ] 11.1 Unit tests for config loading (base + overrides + env vars)
- [ ] 11.2 Unit tests for validation (valid config passes; invalid config fails with clear errors)
- [ ] 11.3 Integration test hot-reload (change retrieval weights; verify new weights used; verify config_version incremented)
- [ ] 11.4 Test feature flags (disable SPLADE → verify SPLADE skipped; fusion weights auto-adjusted)

## 12. Documentation

- [ ] 12.1 Document config.yaml structure with examples
- [ ] 12.2 Create config tuning guide (common adjustments: retrieval weights, chunking profiles, rate limits)
- [ ] 12.3 Document hot-reload procedure (when safe; when requires restart)
- [ ] 12.4 Document secrets management (Vault integration, placeholder syntax)
