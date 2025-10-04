# Ledger Maintenance & Enum Enforcement

The ingestion ledger now rejects string-based states and the legacy
`LedgerState.LEGACY` placeholder. This runbook describes the operational
checklist for keeping ledgers compacted, telemetry clean, and dashboards
accurate during and after the migration.

## Pre-Maintenance Checklist

- [ ] Export the active ledger (`scp ingest:/var/lib/medkg/ledger.jsonl ./ledger.jsonl`).
- [ ] Run `python scripts/ops/ledger_audit.py ledger.jsonl` to ensure no `legacy`
      markers or unknown states remain.
- [ ] Capture Prometheus snapshots for `med_ledger_documents_by_state` and
      `med_ledger_state_transitions_total` for before/after comparison.
- [ ] Confirm the "Ledger State Distribution" panel on Grafana dashboard
      `medkg-pipeline` shows only enum names (no `legacy`).

## Backup and Compaction

1. Create an S3 backup: `aws s3 cp ledger.jsonl s3://medkg-backups/ledger/$(date +%F)/`.
2. Snapshot the live instance: `med ledger snapshot --ledger-path /var/lib/medkg/ledger.jsonl`.
3. Compact the ledger on staging first:
   ```bash
   med ledger compact --ledger-path /var/lib/medkg/ledger.jsonl --snapshot-dir /var/lib/medkg/ledger.snapshots
   python scripts/ops/ledger_audit.py /var/lib/medkg/ledger.jsonl
   ```
4. Smoke test staging services (PDF ingestion, IR builder, CLI auto mode).
5. Repeat the compaction on production during the approved maintenance window.

## Verification

- Run `python scripts/ops/ledger_audit.py --fail-on-warnings /var/lib/medkg/ledger.jsonl` post-compaction.
- Execute `rg "\"legacy\"" /var/lib/medkg/ledger.jsonl` (should return no matches).
- Load the compacted ledger locally and ensure initialization remains under one
  second using `python scripts/benchmarks/ledger_benchmark.py --documents 10000`.
- Spot-check the audit trail with `med ledger history <doc_id>` to verify enum
  serialization (`old_state`/`new_state` are uppercase names).

## Telemetry & Dashboards

- Prometheus alert `LegacyLedgerStateDetected` (component=ingestion) fires if a
  `legacy` label reappears. Acknowledge, run the audit script, and compact.
- Grafana panel "Ledger State Distribution" visualises
  `med_ledger_documents_by_state` without the legacy bucket. Exported JSON lives
  at `ops/monitoring/grafana/pipeline-overview.json`.
- Alert `LedgerInvalidTransitions` tracks `med_ledger_errors_total{type="invalid_transition"}`.

## Communication & Rollout

- Slack template:
  > *Subject*: Ledger enum-only enforcement
  >
  > Compaction starts at <time>. Ledger snapshots stored at s3://medkg-backups/ledger/<date>.
  > New alert `LegacyLedgerStateDetected` in place; watch Grafana panel "Ledger State Distribution".
- Update release notes / changelog referencing the removal of `LedgerState.LEGACY`.
- Notify operations when the audit script finishes cleanly to lift the
  maintenance window.

## Post-Deployment Monitoring

- Watch `med_ledger_documents_by_state` for abnormal spikes in `failed` or `retrying`.
- Ensure `med_ledger_errors_total{type="invalid_transition"}` remains flat.
- Review ingestion service logs for `TypeError: new_state must be a LedgerState`.
- Confirm Grafana alerts remain quiet for at least one hour post-deployment.
- Document outcomes and lessons learned in the release record.

## Rollback

- Restore the latest snapshot from `ledger.snapshots/`.
- Re-import the previous Grafana dashboard JSON if customisations regressed.
- Disable the new alerts temporarily if they block the rollback; re-enable after restoration.
