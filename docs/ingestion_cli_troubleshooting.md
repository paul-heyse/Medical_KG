# Unified Ingestion CLI Troubleshooting

## Quick Diagnostics

1. Run with `--verbose` to capture detailed adapter logging (sets log level to DEBUG).
2. Enable `--error-log errors.jsonl` to append machine-readable failure reports for offline triage.
3. Combine `--summary-only` with `--output json` to feed results into monitoring pipelines.

## Common Issues

| Symptom | Diagnosis | Next Steps |
| --- | --- | --- |
| CLI exits with code 2 and prints `Schema validation failed` | NDJSON payload violates supplied JSON Schema | Inspect the JSON pointer in the error message. Use `jq`/`python -m json.tool` to inspect offending records. Update producer or schema accordingly. |
| CLI warns `Validation skipped by user request` | `--skip-validation` set | Confirm this is intentional; remove flag for production jobs or add schema validation to catch drift. |
| No progress bar displayed | CLI running in non-TTY environment or `--quiet` set | Force display with `--progress`. For CI logs keep `--summary-only` to avoid clutter. |
| Delegation warning appears | Legacy command path still used | Update invocation to `med ingest <adapter>`; CI checker will fail until command is migrated. |
| `IngestionPipeline.run_async_legacy()` AttributeError | Deprecated wrapper removed | Update automation to call `stream_events()` or `run_async()` instead; rerun smoke tests after patching. |
| `jsonschema is required when using --schema` | Dependency missing from environment | Install via `micromamba install -p ./.venv jsonschema` (preferred) or `pip install jsonschema`. |
| Batch file reported as empty under strict validation | NDJSON file contains blank lines or whitespace only | Verify file contents and rerun without `--strict-validation` if necessary. |

## Advanced Debugging

- **Replay a single document:** use `--id <doc_id> --summary-only --verbose` to isolate adapter output.
- **Throttle auto mode:** `--auto --rate-limit 0.5` will call the adapter every two seconds; combine with `--page-size` to tune throughput.
- **Dry-run before production:** `--dry-run` still enforces schema + NDJSON validation (unless `--skip-validation`) allowing quick smoke checks during incidents.

## Support Channels

- `#medical-kg` Slack for engineering questions.
- Ops on-call via PagerDuty (see `docs/operations_manual.md`).
- File issues in the ingestion board with summary + CLI JSON output when raising bugs.

