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

## Schema Validation

All configuration files declare a `$schema` pointer (for example `./config.schema.json#v1.0.0`). The loader resolves `config.schema.json`, verifies it targets JSON Schema Draft 7, and enforces the declared schema version. Configurations pinned to an older schema load successfully but emit a warning that references `MEDCFG_ALLOW_OLD_SCHEMA` so operators can decide whether to keep accepting historical payloads. Set `MEDCFG_ALLOW_OLD_SCHEMA=0` to fail fast on older versions. If a configuration references a newer schema version the reload fails with guidance to migrate to the supported release. Update the `$schema` pointer and adjust any renamed fields when the schema version advances.

### Custom Formats

`config.schema.json` registers project-specific formats in addition to the JSON Schema defaults:

| Format | Purpose | Examples |
| --- | --- | --- |
| `duration` | Human-friendly durations used by schedulers. | `"5m"`, `"15m"`, `"1h"` |
| `adapter_name` | Validates ingestion adapters against the registry. | `"pubmed"`, `"pmc"`, `"loinc"` |

Invalid values surface in validation errors with JSON Pointer locations and remediation hints, making it easier to spot typos or unsupported adapters.

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

### `pipelines`

Defines runtime orchestration for ingestion and document processing. The `pdf` block configures artifact paths and GPU requirements for the PDF pipeline. The optional `pipelines.scheduled` array registers recurring ingestion jobs; each entry declares an `adapter` (validated against the adapter registry), an execution `interval` using the `duration` format, and an optional `enabled` flag to stage schedules without activating them.

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
