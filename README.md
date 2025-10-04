# Medical_KG (replace via scripts/init.sh)

Baseline template for Python projects in Cursor on Ubuntu.

## Quick start (per project)
1. Run `scripts/init.sh <package_name> [python_version] "Description"`.
2. Open folder in Cursor (`cursor .`).
3. Ensure interpreter shows `.venv/bin/python`.
4. Run target tasks: **pytest**, **lint**, **format**.
5. Invoke the unified ingestion CLI: `med ingest <adapter> --help` for an overview, then run batch jobs such as `med ingest demo --batch samples.ndjson --schema schemas/demo.json`.

See `.cursor/rules`, `.vscode/*`, and `environment.yml` for configuration details.

## Optional dependencies

Optional capabilities such as observability, PDF ingestion, embeddings, and load
testing are shipped as extras. Review the [dependency matrix](docs/dependencies.md)
for the full list of groups and install commands. The CLI surfaces a diagnostic
view via `med dependencies check` (add `--json` for automation pipelines).

## Unified Ingestion CLI

- Primary entry point: `med ingest ADAPTER [OPTIONS]`.
- Highlights: dynamic adapter listing in help output, JSON Schema validation via `--schema`, Rich-powered progress bars, and JSON/table summaries.
- Historical migration materials are archived under `docs/archive/cli_unification/`.

## Testing & Coverage

- Run `pytest -q` to execute the offline suite. A trace-based hook enforces at
  least **95% statement coverage** for `src/Medical_KG` and writes
  `coverage_missing.txt` whenever new gaps appear.
- Review `docs/testing_strategy.md` for guidance on fixtures, async helpers, and
  coverage expectations.
