# Medical_KG (replace via scripts/init.sh)

Baseline template for Python projects in Cursor on Ubuntu.

## Quick start (per project)
1. Run `scripts/init.sh <package_name> [python_version] "Description"`.
2. Open folder in Cursor (`cursor .`).
3. Ensure interpreter shows `.venv/bin/python`.
4. Run target tasks: **pytest**, **lint**, **format**.

See `.cursor/rules`, `.vscode/*`, and `environment.yml` for configuration details.

## Testing & Coverage

- Run `pytest -q` to execute the offline suite. A trace-based hook enforces 100%
  statement coverage for `src/Medical_KG`; adjust `coverage_budget.json` only
  when shrinking uncovered allowances.
- Review `docs/testing_strategy.md` for guidance on fixtures, async helpers, and
  the maintenance workflow for the coverage budget.
