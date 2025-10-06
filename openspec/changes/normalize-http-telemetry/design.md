## Context
The `add-http-client-telemetry` proposal introduced lifecycle hooks and a shared `_TelemetryRegistry`, yet the runtime still ships `_NoopMetric` placeholders, implicit Prometheus auto-detection, and adapter-specific metric wiring. This mismatch confuses operators, produces duplicate metrics registration, and hides the explicit enablement model described in the optimisation package. Normalising the HTTP telemetry surface ensures the client, adapters, and documentation all reflect the approved design.

## Goals / Non-Goals
- **Goals**
  - Remove placeholder `_NoopMetric` classes and funnel all instrumentation through `_TelemetryRegistry`.
  - Make metrics configuration explicit via application settings or constructor flags instead of implicit Prometheus probing.
  - Update adapters/tests/runbooks to reference the unified registry and lifecycle callbacks.
  - Guarantee idempotent metric registration and consistent label sets across HTTP ingest workloads.
- **Non-Goals**
  - Redesign the callback interfaces delivered by `add-http-client-telemetry` (they remain authoritative).
  - Introduce new observability backends beyond those already supported (Prometheus/OpenTelemetry).
  - Expand telemetry to non-HTTP subsystems; scope is the HTTP client and its adapters.

## Decisions
- Delete `_NoopMetric` scaffolding and expose a minimal stub in tests only where necessary.
- Require callers to set `enable_metrics` (or config equivalent) to register collectors; default remains disabled for deterministic behaviour.
- Centralise all metric creation in `_TelemetryRegistry`, which is responsible for ensuring single registration and providing reusable counters/gauges.
- Replace adapter-specific metric wiring with helpers that request handles from the registry.
- Document the configuration flow in operator runbooks, including example Prometheus configuration.

## Risks / Trade-offs
- **Risk:** Removing implicit detection may surprise deployments relying on auto-enabled metrics. *Mitigation:* Provide clear release notes and a backwards-compatible configuration shim that warns when implicit behaviour is detected.
- **Risk:** Consolidating registration could surface naming collisions if legacy collectors used different label sets. *Mitigation:* Audit metric names/labels and add tests to enforce expected schemas.
- **Trade-off:** Additional guard code ensures idempotent registration, adding minor overhead at startup. *Mitigation:* Execute guards once per process; subsequent requests use cached collectors.

## Migration Plan
1. Remove `_NoopMetric` and Prometheus auto-detection from the HTTP client module.
2. Enhance `_TelemetryRegistry` with explicit registration helpers and idempotent guards.
3. Update HTTP adapters to acquire metrics from the registry and honour the explicit enablement flag.
4. Refresh unit/integration tests to validate registration flow, label sets, and disabled-mode behaviour.
5. Update operations documentation to describe the new configuration steps and include validation commands.

## Open Questions
- Do any deployments depend on implicit metrics enablement for health checks? Coordinate with operations to confirm.
- Should the default configuration emit a deprecation warning when `enable_metrics` is unset but Prometheus endpoints are scraped? Requires product decision.
- Are there planned additional telemetry collectors (e.g., histograms) that should be accounted for in the registry abstractions?
