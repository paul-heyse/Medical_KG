# Add Telemetry Hooks to AsyncHttpClient

## Why

The shared `AsyncHttpClient` handles retries and rate limiting but:

- No hooks for logging retry attempts
- Queue saturation invisible
- Per-host metrics require custom wrappers
- Throttling issues hard to diagnose
- Each adapter builds one-off telemetry

From `repo_optimization_opportunities.md`: "The shared `AsyncHttpClient` handles retries and rate limiting internally but only records high-level counters and lacks structured hooks for logging retry attempts, saturation, or payload metadata."

## What Changes

- Add callback hooks: `on_request`, `on_retry`, `on_backoff`, `on_response`
- Emit structured `HttpEvent` instances for HTTP lifecycle
- Expose limiter queue times as Prometheus histograms
- Add per-host instrumentation support
- Document telemetry patterns for adapters
- Keep hooks optional (no overhead if unused)

## Impact

- **Affected code**: `src/Medical_KG/ingestion/http_client.py` (+120 lines)
- **Benefits**: Observable throttling, diagnosable rate limits, standardized telemetry
- **Breaking changes**: None (hooks are opt-in)
- **Risk**: Low - additive changes, backwards compatible
