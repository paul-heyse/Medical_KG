# ARCHIVED: Unified Ingestion CLI Rollout Plan

_Archived 2025-10-04 – Migration milestones completed._

## Timeline

| Milestone | Owner | Target |
| --- | --- | --- |
| Announce deprecation timeline in #medical-kg and email alias | Product Ops | Week 0 |
| Update internal docs/runbooks (this repo + Confluence) | DevEx | Week 0 |
| Staging smoke tests with production-sized NDJSON | Ingestion Ops | Week 1 |
| CI migration checker enforced (no warnings) | Platform Eng | Week 2 |
| Production deployment with monitoring | Platform Eng | Week 3 |
| Adoption metrics review (target ≥95% unified CLI usage) | Analytics | Week 8 |
| Remove delegates (change `remove-legacy-ingestion-cli`) | Platform Eng | Week 12 |

## Communication Artifacts

- Slack/email template in `docs/ingestion_cli_migration_guide.md`.
- Docs updated: `docs/ingestion_runbooks.md`, `docs/ingestion_cli_reference.md`, `README.md`, `docs/operations_manual.md`.
- Troubleshooting aid: `docs/ingestion_cli_troubleshooting.md`.

## Monitoring & Metrics

- Log delegate invocations via `Medical_KG.cli` logger (already implemented) and ingest into adoption dashboard.
- Track `--schema` usage to confirm validation guardrails are adopted.
- Alert when legacy commands appear by running `scripts/cli_migration/check_ci_commands.py` in CI.

## Deployment Steps

1. **Staging** – run benchmark harness (`scripts/benchmarks/ingestion_cli_benchmark.py`) and real adapter dry-runs with ledger snapshot.
2. **Production** – deploy after staging sign-off; monitor logs for delegate warnings and ingestion failure rates.
3. **Rollback** – legacy delegate remains available for 3 months; use env var `MEDICAL_KG_SUPPRESS_INGEST_DEPRECATED=1` in automation if needed.

## Adoption Tracking

- Weekly report summarising delegate usage counts and number of migration warnings emitted.
- Identify lagging teams and coordinate office hours to assist with migration.

