# Configuration Schema Migration Guide

This guide walks operators through safely upgrading `config.schema.json` versions using the jsonschema-powered toolchain.

## Prerequisites

- Confirm `config.schema.json` and `docs/config_schema_changelog.md` document the new version.
- Regenerate the reference docs if desired: `python scripts/generate_config_docs.py --output docs/config_schema_reference.md`.
- Ensure you have access to the environment-specific overrides (`config-*.yaml`) and secrets.

## Step-by-step workflow

1. **Validate current payloads** – run `python scripts/validate_all_configs.py --no-color` from the repo root. This confirms every environment file still conforms to the existing schema before attempting a migration.
2. **Dry-run the migration** – execute `med config migrate-schema --config-dir src/Medical_KG/config --target-version <new-version> --write ./tmp/migrated.yaml`. Review the emitted steps list; it should mention each structural change (`update-$schema`, new defaults, etc.).
3. **Re-validate the migrated payload** – run `python scripts/validate_all_configs.py --config-dir ./tmp --no-color` (or point directly at the migrated file) to ensure the output satisfies the new schema.
4. **Update documentation** – append the scenario to `docs/config_schema_changelog.md` and note any operator actions in `docs/operations_manual.md`.
5. **Roll forward configs** – check in the migrated files or propagate via the deployment pipeline.

## Staging rehearsal

Before touching production, rehearse on staging:

- Merge the baseline config with `config-staging.yaml` and run `med config migrate-schema --env staging`. The CLI surfaces the same migration steps used in production, ensuring there are no environment-specific surprises.
- Validate the merged payload with `python scripts/validate_all_configs.py --config-dir src/Medical_KG/config --no-color`; the script already walks every environment file, so staging coverage is automatic.
- Deploy to staging and monitor for validation failures surfaced by `ConfigManager` hot-reload guards.

## Production rollout

1. Capture a snapshot of `config.yaml` and `config-prod.yaml` in source control.
2. Run `med config migrate-schema --env prod --write ./tmp/config-prod.yaml` to materialise the migrated payload.
3. Commit or promote the migrated file alongside the schema change.
4. Execute `python scripts/validate_all_configs.py --no-color` in CI (the workflow step added in this change runs automatically).
5. Ship to production and monitor metrics:
   - `config_info` should expose the new schema hash.
   - No `ConfigError` entries should appear in logs.

## Post-deployment monitoring

- Keep the legacy validator disabled for at least 30 days (already enforced in code) before removing compatibility shims.
- Review `docs/config_schema_changelog.md` to ensure the migration is documented for posterity.
- If regressions occur, roll back by reapplying the captured config snapshot and rerunning the validation script.

## Quick checklist

- [ ] Validate existing configs with `scripts/validate_all_configs.py`.
- [ ] Run `med config migrate-schema` for the target environment(s).
- [ ] Re-validate migrated payloads.
- [ ] Update changelog and operations documentation.
- [ ] Promote to staging, monitor, then promote to production.
- [ ] Confirm observability signals remain healthy for 30 days.
