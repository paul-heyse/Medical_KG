# Continuous Improvement Cadence

## Weekly Metrics Review (Ops Sync)

- Review KPI dashboard (latency, error rate, SHACL violations, GPU utilisation).
- Compare against SLO budgets from `ops/load_test/budget.yaml`.
- Track recurring incidents and assign owners for remediation tasks.

## Monthly Retrospective

- Rotate facilitator; capture action items in ops board.
- Review cost dashboards (GPU spend, storage usage) and adjust retention policies.
- Evaluate automation opportunities (e.g., new runbooks → scripts).

## Quarterly Drills

- **Disaster Recovery** – Execute `ops/release/pipeline.md` in staging, restore from backups, run E2E harness.
- **Chaos Engineering** – Schedule full `ops/chaos/chaos_tests.sh --scenario all` with CHAOS_APPROVED=1.
- Update documentation (`docs/operations_manual.md`) with findings.

## KPI Targets

| Metric                             | Target                      |
|------------------------------------|-----------------------------|
| `/retrieve` P95 latency            | < 900 ms                    |
| API error rate                     | < 1%                        |
| SHACL violation rate               | 0 (alerts at ≥ 1)           |
| GPU utilisation (steady state)     | 60-85%                      |
| Catalog refresh diff               | < 1% doc count delta        |

Track progress in the `Continuous Improvement` project board. Close action items with links to PRs/runbooks.
