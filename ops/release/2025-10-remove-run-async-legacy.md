# Release Plan: Remove `run_async_legacy`

## Timeline

- **2025-10-08** – Final code freeze; regression tests executed on staging.
- **2025-10-10** – Publish release announcement draft and share with stakeholders.
- **2025-10-11** – Deploy to staging during daytime window, monitor telemetry for 24h.
- **2025-10-12** – Production deployment during maintenance window (02:00-03:00 UTC).

## Pre-Deployment Checklist

- [x] Confirm no services call `run_async_legacy()` (search telemetry + code).
- [x] Ensure dashboards/prometheus rules updated to flag any reintroduction of the legacy label.
- [x] Update docs (`docs/ingestion_runbooks.md`, `docs/operations_manual.md`, `CONTRIBUTING.md`).
- [x] Notify dependent teams (clinical ingestion, reporting automation) of breaking change.

## Communication

- Slack `#medical-kg` announcement referencing CHANGELOG entry and upgrade path.
- Email blast to platform stakeholders summarising API removal and fallback plan.
- Status page maintenance notice scheduled 48h in advance.

## Rollout Steps

1. Deploy ingestion service to staging.
2. Run `med ingest nice --dry-run --stream` smoke test.
3. Verify Prometheus alert `LegacyPipelineModeDetected` stays inactive.
4. Promote to production via ArgoCD.
5. Monitor ingestion dashboards (latency, throughput, consumption modes) for 2h.
6. Run post-deploy verification script `ops/e2e/run_verification.py --mode live`.

## Rollback Plan

- Revert deployment via ArgoCD to previous image tag (`medical-kg@2025-10-05`).
- Restore configuration snapshot containing legacy warning toggles if needed.
- Notify stakeholders of rollback and freeze further ingestion changes until root cause identified.

## Post-Deployment Tasks

- Capture metrics snapshots confirming zero `run_async_legacy` labels.
- Close legacy removal tickets in issue tracker.
- Archive related documentation in `docs/legacy/`.
- Update roadmap to reflect completion (Q4 milestone).
