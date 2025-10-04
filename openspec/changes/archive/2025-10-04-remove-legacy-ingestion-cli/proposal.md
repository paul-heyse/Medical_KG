# Remove Legacy Ingestion CLI

## Why

After completing `extract-ingestion-cli-shared-helpers` and `implement-unified-ingestion-cli`, we have:

- ✅ Shared helpers for all CLI operations
- ✅ Unified CLI with all features
- ✅ Deprecation warnings and delegates in place
- ✅ Migration guide published

After the **3-month migration period**, users have adopted the unified CLI. The legacy CLI code and delegates now represent:

**Technical debt**:

- Dead code paths maintained by tests
- Deprecation delegates adding complexity
- Confusing codebase for new contributors
- CI overhead testing both paths

**User confusion**:

- Deprecated commands still discoverable
- Documentation must explain legacy vs unified
- Support burden for "old way" questions

**Repository review context**: "Fully removing the legacy CLI after successful migration would eliminate the final source of duplication and simplify the ingestion interface."

This proposal **completes the CLI unification** by removing deprecated code after confirming migration success.

## What Changes

### Remove Legacy CLI Code

- Delete deprecated CLI entry points from `Medical_KG.cli`
- Remove deprecation delegate functions
- Remove legacy-specific tests
- Clean up migration warning code

### Update Entry Points

- Remove legacy entry point configurations
- Ensure only `med ingest` remains
- Update packaging metadata
- Clean up `__main__.py`

### Final Documentation Cleanup

- Remove migration guides (no longer needed)
- Remove legacy CLI sections from docs
- Update all examples to unified CLI only
- Archive migration tracking metrics

### Code Simplification

- Remove conditional logic for deprecated flags
- Remove migration tracking/logging code
- Simplify test suite (single CLI path)
- Clean up environment variable checks

## Impact

- **Affected specs**: ingestion (CLI interface finalized)
- **Affected code**:
  - `src/Medical_KG/cli.py` (delete deprecated code, -200 lines)
  - `src/Medical_KG/__main__.py` (simplify entry points, -30 lines)
  - `pyproject.toml` (remove legacy entry points)
  - `tests/ingestion/test_legacy_cli.py` (delete, -150 lines)
  - `tests/ingestion/test_cli_migration.py` (delete, -100 lines)
  - `docs/cli_migration_guide.md` (archive or delete)
  - `docs/ingestion_runbooks.md` (remove migration sections, -50 lines)
- **Benefits**:
  - **Simpler codebase**: ~500 lines of dead code removed
  - **Clearer for contributors**: Single CLI implementation
  - **Reduced test overhead**: No legacy path testing
  - **Finalized interface**: Clear that unified CLI is the only way
- **Breaking changes**: **YES** - legacy commands removed
  - Users who didn't migrate will experience hard failure
  - Requires major version bump (e.g., 2.0.0)
- **Risk**: High for unmigrated users, low for migrated users
- **Prerequisites**:
  - Migration metrics show >95% adoption
  - No critical issues reported with unified CLI
  - Minimum 3 months since deprecation warnings added

## Prerequisites Before Implementation

This proposal should **NOT** be implemented until:

1. ✅ `extract-ingestion-cli-shared-helpers` deployed to production
2. ✅ `implement-unified-ingestion-cli` deployed to production
3. ✅ 3 months have passed since deprecation warnings enabled
4. ✅ Adoption metrics show >95% using unified CLI
5. ✅ Zero critical bugs reported for unified CLI
6. ✅ Internal CI/CD fully migrated
7. ✅ Final migration announcement sent (2 weeks before removal)

## Migration Verification Checklist

Before proceeding with this proposal, verify:

- [ ] Deprecation warning logs show declining usage
- [ ] Latest week shows <5% legacy CLI usage
- [ ] No new issues filed about unified CLI in 30 days
- [ ] All internal tooling updated (checked via CI audit)
- [ ] External users notified (changelog, mailing list, Slack)
- [ ] Rollback plan documented (revert to previous version)
