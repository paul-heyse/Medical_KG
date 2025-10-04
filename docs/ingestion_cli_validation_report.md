# Unified Ingestion CLI Validation Report

## 16.1 Full Test Suite
- `ruff check src tests`
- `python -m mypy --strict src/Medical_KG/ingestion src/Medical_KG/ir`
- `pytest -q`

Results recorded in CI and local runs (see PR summary). All suites pass after introducing schema validation + help text changes.

## 16.2 Staging Dry-Run (Planned)
- Execute `med ingest <adapter> --batch staging.ndjson --schema schema.json --dry-run` against staging ledger.
- Owners: Ingestion Ops (Morgan Ellis) prior to deploying to production.

## 16.3 Legacy Parity Check
- `tests/ingestion/test_ingest_cli.py::test_ingest_translates_legacy_flags` ensures the delegate produces identical argv sequences.
- `scripts/cli_migration/suggest_flag_migrations.py` exercises `_translate_legacy_args` on arbitrary commands.

## 16.4 Terminal Matrix
- Unit coverage in `tests/ingestion/test_cli_helpers.py` verifies `should_display_progress` decisions for TTY vs non-TTY and forced enable/disable scenarios.
- Manual smoke test: run `med ingest demo --batch sample.ndjson --summary-only` piping to a file to confirm progress disables automatically.

## 16.5 Cross-Platform Verification (Planned)
- CI matrix addition pending: run smoke job on `macos-latest` and `windows-latest` executing `med ingest --help` and schema dry-run using sample data.

## 16.6 Performance Benchmark (Planned)
- Target dataset: 10k NDJSON records; measure throughput before/after unification to confirm no regressions.
- Script placeholder: `scripts/benchmarks/ingestion_cli_benchmark.py` (to be implemented as part of rollout readiness).

