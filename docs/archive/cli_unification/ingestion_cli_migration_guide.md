# ARCHIVED: Unified Ingestion CLI Migration Guide

_Archived 2025-10-04 – Migration completed and tooling retired._

The legacy ingestion entry points (`med ingest --source ...` and `med-ingest ...`) now delegate to the unified Typer-based CLI. Use this guide to update scripts, CI jobs, and operator runbooks.

## Migration Checklist

1. **Inventory usage** – run `scripts/cli_migration/check_ci_commands.py --json` to identify legacy commands in workflows, scripts, and automation.
2. **Rewrite flags** – pipe each command through `scripts/cli_migration/suggest_flag_migrations.py` to obtain an equivalent unified invocation.
3. **Validate locally** – execute `med ingest <adapter> --dry-run --summary-only` with migrated flags to ensure payloads parse and ledger state resolves.
4. **Update CI** – commit the translated commands and ensure the CI migration checker passes with zero findings.
5. **Communicate** – share the announcement template (see below) with downstream consumers before flipping production pipelines.
6. **Audit eager pipeline usage** – run `scripts/check_streaming_migration.py` to find remaining `run_async`/`run_async_legacy` calls and plan their transition to `stream_events()`.

## Flag Translation Reference

| Legacy Syntax | Unified Syntax |
| --- | --- |
| `med ingest --source umls --batch-file data.ndjson` | `med ingest umls --batch data.ndjson` |
| `med-ingest pubmed --continue-from-ledger --max-records 500` | `med ingest pubmed --resume --limit 500` |
| `med ingest --source nice --ids a,b,c` | `med ingest nice --id a --id b --id c` |

## Schema Validation Adoption

- Supply `--schema path/to/schema.json` alongside `--batch` to validate each NDJSON record against the documented payload contract.
- When `jsonschema` is unavailable the CLI emits a user-friendly error instructing how to install the dependency via micromamba or pip.
- CI should include the schema in repositories to guarantee parity between staging and production batches.

## Communication Template (Task 15.4)

```
Subject: Unified ingestion CLI now available (legacy commands deprecating in 3 months)

Hi team,

We have released the unified ingestion CLI: `med ingest <adapter> [options]`. Existing commands such as `med-ingest` and `med ingest --source ...` now delegate with a warning and will be removed in 3 months.

Action items:
1. Update scripts/CI to use the new syntax (`scripts/cli_migration/suggest_flag_migrations.py` can assist).
2. Adopt the JSON Schema guardrail (`--schema`) where batch NDJSON files are used.
3. Reach out in #medical-kg if migration blockers arise.

Thanks,
Medical KG Platform
```

## Troubleshooting

| Symptom | Cause | Resolution |
| --- | --- | --- |
| `jsonschema is required when using --schema` | Optional dependency missing | Install via `micromamba install -p ./.venv jsonschema` or remove `--schema`. |
| `Unknown source 'foo'` | Adapter not registered | Run `med ingest --help` to review valid adapters; ensure registry entry exists. |
| Progress bar not showing | Non-TTY or `--quiet` set | Force display with `--progress`. |
| Schema validation failed | NDJSON violates schema | Inspect error log/line number, update payload generator or schema. |

## Timeline

- **Week 0** – Unified CLI shipped; warnings enabled by default.
- **Week 4** – Expect >75% of automation migrated; monitor CI checker output.
- **Week 8** – Target 95% adoption; escalate stragglers via operations stand-up. Begin tracking streaming adoption via the migration script.
- **Week 12** – Remove delegates as part of `remove-legacy-ingestion-cli` change (see roadmap).

