# Proposal: Remove Legacy Ingestion Tooling

## Why

The CLI unification (Phase 3) successfully consolidated all ingestion commands under `med ingest <adapter>`, achieving >95% adoption. Legacy CLI migration scripts (`scripts/cli_migration/`), compatibility checks, and operations guides still reference deprecated commands. These artifacts encourage backsliding and create maintenance burden when updating flags or documentation.

## What Changes

- **Delete migration scripts**: Remove `scripts/cli_migration/*.py` and related tooling
- **Archive migration playbook**: Move CLI migration documentation to historical archive
- **Remove command references**: Purge legacy CLI examples from operational documentation
- **Delete environment variables**: Remove migration-specific env vars and warning macros
- **Clean up tooling docs**: Update contributor guides to reference only unified CLI
- **Update release checklist**: Remove migration validation steps

## Impact

**Affected specs**: `ingestion` (CLI tooling)

**Affected code**:

- `scripts/cli_migration/` - Delete entire directory (~8 files, 500 lines)
- `scripts/check_streaming_migration.py` - Delete migration verification script
- `docs/operations_manual.md` - Remove legacy command references
- `CLI_UNIFICATION_ROADMAP.md` - Archive migration timeline
- `CLI_UNIFICATION_SUMMARY.md` - Mark as historical reference
- `.github/workflows/` - Remove legacy CLI test jobs

**Breaking Change**: NO - only removes tooling, not user-facing APIs

**Migration Path**: N/A - tooling is for internal use only

**Benefits**:

- -500 lines of migration-only code removed
- Clearer documentation focused on current CLI
- Reduces confusion for new contributors
- Eliminates maintenance burden for outdated scripts
- Prevents accidental usage of deprecated patterns
