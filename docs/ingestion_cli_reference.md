# Unified Ingestion CLI Reference

## Command Synopsis

```
med ingest ADAPTER [OPTIONS]
```

- `ADAPTER` – required positional argument; tab-completable list of adapters registered in `Medical_KG.ingestion.registry`.
- Options accept either the long form or the documented short aliases.

## Core Options

| Option | Alias | Description |
| --- | --- | --- |
| `--batch PATH` | `-b` | NDJSON batch file containing adapter parameters. File existence verified before execution. |
| `--id VALUE` | – | Repeatable flag to target specific document identifiers. |
| `--resume` | `-r` | Resume from ledger checkpoints (translates `--continue-from-ledger`). |
| `--auto` | – | Enable streaming auto mode (emits doc IDs as they complete). |
| `--limit N` | `-n` | Cap number of parameter rows or auto-mode iterations processed. |
| `--output text|json|table` | `-o` | Select output format (text default, JSON for automation, Rich table for operators). |
| `--summary-only` | – | Emit aggregated summary without per-result lines. |
| `--show-timings` | – | Include run duration in summaries. |
| `--schema PATH` | – | Validate NDJSON records against JSON Schema (requires `jsonschema`). |
| `--dry-run` | – | Validate inputs and ledger state without invoking adapters. |
| `--strict-validation` | – | Reject empty batch files and enforce strict NDJSON parsing. |
| `--skip-validation` | – | Skip optional validation (still records warning in summary). |
| `--fail-fast` | – | Abort on first adapter failure. |
| `--progress / --no-progress` | – | Force enable/disable Rich progress bar. Defaults to auto-detect TTY.
| `--start-date/--end-date` | – | ISO8601 timestamps to bound auto mode fetch ranges. |
| `--page-size` | – | Override adapter pagination chunk size. |
| `--rate-limit` | – | Throttle adapter invocations per second. |
| `--ledger PATH` | – | Custom ingestion ledger path (default `.ingest-ledger.jsonl`). |
| `--log-level LEVEL` | – | Logging severity (INFO default). |
| `--log-file PATH` | – | Write structured logs to file instead of stderr. |
| `--error-log PATH` | – | Append JSONL error entries for offline triage. |
| `--verbose` | `-v` | Enable verbose (DEBUG) logging. |
| `--quiet` | `-q` | Suppress non-essential output (progress bars off). |
| `--version` | – | Print CLI version and exit. |

## Output Formats

- **Text** – Default human-readable summary. Warnings/errors are prefixed and timing info is optional via `--show-timings`.
- **JSON** – Machine-consumable structure produced by `render_json_summary`; include in CI pipelines or dashboards.
- **Table** – Rich-rendered table (requires `rich`) ideal for operators; auto-falls back to text when `rich` unavailable.

## Schema Validation Workflow

1. Define a JSON Schema describing each NDJSON record.
2. Run `med ingest <adapter> --batch payload.ndjson --schema schema.json`.
3. On validation failure the CLI exits with code `2` and prints the failing pointer (`<root>` or JSON path).
4. Use `--error-log errors.jsonl` to capture validation failures for auditing.

## Exit Codes

| Code | Meaning |
| --- | --- |
| `0` | Successful execution (may still include warnings). |
| `1` | Adapter runtime failures (after summary emission). |
| `2` | Invalid usage (bad parameters, schema violations, missing files). |

## Related Documentation

- `docs/ingestion_runbooks.md` – Operational runbooks and examples.
- `docs/ingestion_cli_migration_guide.md` – Migration playbook and communication template.
- `docs/ingestion_cli_troubleshooting.md` – Extended troubleshooting recipes.

