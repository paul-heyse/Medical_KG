# Configuration Tuning Guide

Use this guide to adjust runtime parameters safely.

## Retrieval Fusion Weights

1. Update `retrieval.fusion.weights` in `config-override.yaml` or the environment-specific file.
2. Run `med config validate --strict` to confirm the weights sum to 1.0.
3. POST to `/admin/reload` (see [Hot Reload](hot_reload.md)) to apply the change without restarting.
4. Monitor the `feature_flag` and `config_info` metrics to verify rollout.

If SPLADE is disabled (`feature_flags.splade_enabled = false`), weights are redistributed between BM25 and dense automatically.

## Chunking Profiles

- Increase `target_tokens` to produce fewer, longer chunks. Maintain `overlap` at least 5–10% of `target_tokens` for continuity.
- Adjust `tau_coh` upwards to enforce tighter semantic coherence; lower values create more aggressive splitting.
- After editing, validate and hot reload to propagate.

## Rate Limits

`apis.rate_limits` and `sources.*.rate_limit` follow the same structure. Ensure `burst` is at least 25% of `requests_per_minute` to avoid throttling short bursts. Apply overrides and hot reload to update in place.

## Logging Levels

`observability.logging.level` accepts `debug`, `info`, `warn`, or `error`.

- Use `debug` in development for verbose traces.
- Prefer `info` or `warn` in staging/production.
- Hot reload applies the new level immediately.

## Feature Flags

Toggle flags under `feature_flags`. The loader emits a `feature_flag{name="..."}` gauge (1 enabled, 0 disabled) for observability.

## Licensing Gates

Before enabling a vocabulary in `catalog.vocabs`, confirm `policy.yaml` marks it as `licensed: true`. Validation fails if a required license is missing.
