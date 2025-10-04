# Medical_KG (replace via scripts/init.sh)

Baseline template for Python projects in Cursor on Ubuntu.

## Quick start (per project)
1. Run `scripts/init.sh <package_name> [python_version] "Description"`.
2. Open folder in Cursor (`cursor .`).
3. Ensure interpreter shows `.venv/bin/python`.
4. Run target tasks: **pytest**, **lint**, **format**.

See `.cursor/rules`, `.vscode/*`, and `environment.yml` for configuration details.

## Command-line interface

- Use `med ingest <adapter> [options]` for all ingestion workflows. The legacy `med ingest-legacy` alias was removed in version 2.0.0.

## Testing & Coverage

- Run `pytest -q` to execute the offline suite. A trace-based hook enforces at
  least **95% statement coverage** for `src/Medical_KG` and writes
  `coverage_missing.txt` whenever new gaps appear.
- Review `docs/testing_strategy.md` for guidance on fixtures, async helpers, and
  coverage expectations.
