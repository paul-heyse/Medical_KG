# Medical KG Configuration Overview

This document describes the structure of `config.yaml` and the companion files that drive runtime behaviour.

## File Layout

| File | Purpose |
| --- | --- |
| `config.yaml` | Base configuration shared by every environment. |
| `config-dev.yaml` | Local development overrides (mock credentials, verbose logging). |
| `config-staging.yaml` | Staging overrides using non-production credentials. |
| `config-prod.yaml` | Production overrides with strict rate limits and licensing gates. |
| `config-override.yaml` | Optional, not committed – developer specific overrides applied last. |
| `policy.yaml` | Licensing decisions for vocabularies and enforcement actions. |

At runtime the loader merges the files in the order above and applies environment variables (highest precedence).

## Section Reference

### `feature_flags`

Toggle experimental systems such as SPLADE retrieval or extraction pipelines. Flags are evaluated on hot reload so they can be toggled without a full restart.

### `sources`

Defines upstream connectors. Every source entry contains:

- `base_url` – service endpoint.
- `api_key` – secret placeholder resolved from Vault/env.
- `rate_limit` – request throttle (requests per minute and burst capacity).
- `retry` – transient retry policy (attempt count + base back-off seconds).

### `chunking`

Profiles with token and coherence controls for document segmentation. `target_tokens` must be greater than 0 and `overlap` must be less than `target_tokens`.

### `embeddings`

Parameters for the vLLM embedding service (base URL, model name, GPU enforcement) and SPLADE pruning behaviour.

### `retrieval`

Fusion strategy, reranker policy, and neighbour merge heuristics. Fusion weights must sum to 1.0 and are re-balanced automatically if SPLADE is disabled.

### `extraction`

LLM extractor prompts grouped by intent. Each extractor sets the downstream intent (`pico`, `endpoint`, `ae`, `dose`, `eligibility`, or `general`), temperature, max tokens, and a confidence threshold.

### `kg`

Neo4j connectivity and SHACL enforcement toggle. Credentials are supplied via placeholders and resolved at load time.

### `catalog`

Vocabulary ingestion options with refresh cadence and licensing requirements. Each vocabulary references `policy.yaml` to ensure appropriate licensing before import.

### `apis`

API rate limits per scope, JWT authentication details, and CORS allow-list. The `admin_scope` controls access to the reload endpoint.

### `observability`

Logging level (enum: `debug`, `info`, `warn`, `error`), Prometheus push interval, and OpenTelemetry tracing endpoint/sample rate.

### `licensing`

Pointer to the policy file used to gate vocab ingestion and runtime responses.

## Environment Selection

Set `CONFIG_ENV` to `dev`, `staging`, or `prod` to apply the matching overlay file. If unset the loader defaults to `dev` for developer friendliness.
