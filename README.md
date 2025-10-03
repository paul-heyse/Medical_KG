# Medical_KG (replace via scripts/init.sh)

Baseline template for Python projects in Cursor on Ubuntu.

## Quick start (per project)
1. Run `scripts/init.sh <package_name> [python_version] "Description"`.
2. Open folder in Cursor (`cursor .`).
3. Ensure interpreter shows `.venv/bin/python`.
4. Run target tasks: **pytest**, **lint**, **format**.

See `.cursor/rules`, `.vscode/*`, and `environment.yml` for configuration details.

## Testing & Coverage

- Run `pytest` to execute the offline suite. Pytest-cov enforces at least
  **95% statement coverage** for `src/Medical_KG` and automatically produces
  `coverage.xml` plus an `htmlcov/` report for inspection.
- Review `docs/testing_strategy.md` for guidance on typed fixtures, async
  helpers, and coverage expectations.
