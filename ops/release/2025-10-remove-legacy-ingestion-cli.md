# Legacy Ingestion CLI Removal Readiness (2025-10)

## Migration Metrics
- **Unified CLI adoption**: 98.4% of invocations (Datadog dashboard `ingest.cli.adoption`, week ending 2025-09-28).
- **Legacy CLI usage**: 0.6% (automated backfill cron) – job updated 2025-09-29 to unified CLI.
- **Deprecation warnings**: 0 entries in BigQuery `cli_deprecations` table for the past 30 days.
- **Critical bugs**: 0 open issues labeled `cli-unified` in Linear (report pulled 2025-09-30).

## Communications & Approvals
- **External notice**: Migration deadline reminder emailed to customers 2025-09-15 (Mailchimp campaign `cli-phase3-final`).
- **Stakeholder sign-off**: Engineering ✅ (A. Patel), Operations ✅ (J. Rivera), Product ✅ (M. Chen), Support ✅ (L. Gomez).
- **CI/CD audit**: All GitHub Actions workflows updated to `med ingest` as of PR #842 (merged 2025-09-12).

## Rollback Plan
- Tag `v1.9.3` retains legacy CLI entry points; published wheel stored in `s3://medkg-artifacts/releases/v1.9.3/`.
- If rollback required, publish hotfix `v2.0.1` reverting commit `remove-legacy-ingestion-cli` and redeploy via standard release pipeline.
- Announce rollback in `#ops` and customer Slack with template `ops/comms/rollback.md`.

## Test & Validation Checklist
- ✅ Unified CLI regression suite (`pytest -q tests/ingestion`) on staging (2025-10-01).
- ✅ End-to-end ingest load test on staging using unified CLI (ops/load_test report 2025-10-02).
- ✅ Manual verification: `med ingest demo --help` and sample batch run executed on macOS + Windows runners.

## Notes
- Monitoring alerts updated to drop legacy metric names (`ingest_legacy_*`).
- Support playbook updated with "legacy command removed" macro (#284 in Zendesk).
