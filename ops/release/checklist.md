# Release Readiness Checklist

Use this checklist before promoting a build to production. All items must be ✅ before initiating deployment.

## 1. Quality Gates

- [ ] `pytest -q` and `ruff check` pass on the release branch.
- [ ] `ops/e2e/run_verification.py --mode offline` passes in CI.
- [ ] Nightly verification (`.github/workflows/nightly-e2e.yml`) green for the past 3 runs.
- [ ] Load test budgets met (`ops/load_test/check_thresholds.py`).
- [ ] Chaos suite dry-run executed (no outstanding TODOs or skipped tests).

## 2. Observability

- [ ] Prometheus alerts deployed (`ops/monitoring/prometheus-alerts.yaml`).
- [ ] Grafana dashboards (`ops/monitoring/grafana/*.json`) imported and linked to runbooks.
- [ ] Log sampling / trace sampling configured for release (document sample rates).
- [ ] Recent alerts reviewed; outstanding issues resolved or accepted with risk sign-off.

## 3. Data Integrity

- [ ] Backups verified: `aws s3 ls s3://medkg-backups/neo4j/` and `/opensearch/` show <24h freshness.
- [ ] Ledger audit clean: `python scripts/ops/ledger_audit.py releases/<date>/ledger.jsonl` reports no findings.
- [ ] KG SHACL pass-rate ≥ 0.98 over last 24h (see Grafana panel "KG Validation").
- [ ] Catalog diff report reviewed (`ops/runbooks/06-catalog-refresh.md`).

## 4. Deployment Assets

- [ ] Helm values updated for target version (image tag, config hash).
- [ ] Terraform plan reviewed for infrastructure changes (if any).
- [ ] Rollback artefacts prepared: previous image tag, config snapshot, OpenSearch snapshots.
- [ ] Runbooks updated (`ops/runbooks/`).

## 5. Stakeholder Sign-Off

- [ ] Engineering lead approved (checkbox on PR or Slack thread).
- [ ] Operations/on-call acknowledged maintenance window.
- [ ] Domain lead (clinical/medical) reviewed release notes.
- [ ] Security/compliance confirmed no outstanding vulnerabilities.

## 6. Post-Deployment Plan

- [ ] Primary and secondary on-call assigned during rollout.
- [ ] `ops/e2e/run_verification.py --mode live --base-url https://api-staging.medkg.example.com` scheduled immediately post deploy.
- [ ] Metrics watch list agreed (latency, error rate, SHACL, GPU utilisation).
- [ ] Communication template prepared (Slack + status page).

File artefact with timestamp in release record (e.g., `releases/2024-10-03/checklist.md`) and link in the change ticket.
