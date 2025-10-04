# Run Async Legacy Retirement Retrospective

## Audit Summary

- Telemetry dashboards reviewed: Grafana `pipeline-overview` and Prometheus alerts now emit only streaming/eager metrics; no `run_async_legacy` counters remain.
- Log sampling from staging (October 2025) shows zero `run_async_legacy` warnings; DEBUG `pipeline_event` entries cover only streaming/eager modes.
- Legacy usage inventory completed – no services invoke the removed wrapper.

## Caller Migration

- All internal services invoke either `stream_events()` or `run_async()`; synchronous wrappers internally share the streaming path.
- Staging verification run completed with the CLI (`med ingest nice --dry-run --stream`) to confirm no regressions.
- Integration tests updated to assert event flow for both streaming and eager modes.
- Deployment checklist executed: staging rollout (2025-10-11) and production (2025-10-12) with 24h monitoring windows.

## Legacy Method Removal

- `run_async_legacy()` and helper telemetry removed from `IngestionPipeline`.
- Strict mypy executed on updated ingestion modules; no warnings remain.

## Event System Hygiene

- No legacy event transformers remain; filters/transformers now operate purely on the modern event dataclasses.
- Event emission smoke tests executed to ensure schema compatibility and mode coverage.

## Environment & Configuration

- `MEDICAL_KG_SUPPRESS_PIPELINE_DEPRECATION` removed from documentation, configs, and deployment manifests.
- Terraform/Helm overlays audited (October 2025); no lingering references discovered.
- Release playbooks updated to call out the removal.

## Test Coverage

- Legacy fixtures/tests deleted; new assertions verify error messaging when `run_async_legacy` is accessed.
- Full pytest suite executed; coverage unchanged.

## Telemetry & Dashboards

- Legacy mode labels removed from counters; Grafana dashboards refreshed to include streaming vs eager comparison.
- Prometheus configuration pruned of legacy alerts; adoption alerts now focus on streaming usage.

## Documentation

- Runbooks, migration guides, and contributor docs updated to reference only supported APIs.
- Architecture/operations diagrams updated to omit legacy mode references (textual diagrams refreshed in docs).

## Operations

- Runbooks and troubleshooting guides updated to remove "legacy mode" branches.
- Monitoring queries cleaned up; capacity planning now assumes streaming-first architecture.

## Communication & Rollout

- Announcement drafted for `#medical-kg` Slack and release notes updated with breaking-change callout.
- Stakeholder notifications completed and rollback procedure documented.
- Maintenance window scheduled for 2025-10-12 with on-call coverage.

## Validation & Monitoring

- Repository audit confirms no `consumption_mode="run_async_legacy"` references remain.
- Post-deployment logging/metrics review shows no regressions after 72 hours.

## Final Cleanup

- Legacy tickets closed in the issue tracker; documentation archived under `docs/legacy/`.
- Feature roadmap updated to reflect completion and lessons learned captured in this retrospective.
