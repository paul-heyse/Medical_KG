# Implementation Tasks

## 1. Pre-Implementation Validation

- [ ] 1.1 Check adoption metrics (target: >95% unified CLI usage)
- [ ] 1.2 Review deprecation warning logs for trends
- [ ] 1.3 Check bug tracker for unified CLI issues (target: 0 critical)
- [ ] 1.4 Audit internal CI/CD configs for legacy commands
- [ ] 1.5 Verify all external users notified (2+ weeks prior)
- [ ] 1.6 Get stakeholder sign-off for removal
- [ ] 1.7 Document rollback plan

## 2. Identify All Legacy Code

- [ ] 2.1 List all deprecated entry points in `Medical_KG.cli`
- [ ] 2.2 List all deprecation delegate functions
- [ ] 2.3 List all legacy-specific tests
- [ ] 2.4 List all migration warning code locations
- [ ] 2.5 Search codebase for "deprecated" comments
- [ ] 2.6 Create removal checklist

## 3. Remove Deprecated CLI Entry Points

- [ ] 3.1 Remove `ingest-legacy` command from `Medical_KG.cli`
- [ ] 3.2 Remove deprecated flag handling code
- [ ] 3.3 Remove deprecation warning display code
- [ ] 3.4 Remove usage tracking/logging for legacy CLI
- [ ] 3.5 Clean up conditional imports for legacy CLI
- [ ] 3.6 Verify no dangling references

## 4. Update Entry Point Configuration

- [ ] 4.1 Remove legacy entry points from `pyproject.toml`
- [ ] 4.2 Remove legacy entry points from `setup.py` (if exists)
- [ ] 4.3 Ensure `med ingest` is the only ingestion entry point
- [ ] 4.4 Update package metadata (description, classifiers)
- [ ] 4.5 Test entry points after removal (`pip install -e .`)
- [ ] 4.6 Verify console scripts work correctly

## 5. Remove Legacy Tests

- [ ] 5.1 Delete `tests/ingestion/test_legacy_cli.py`
- [ ] 5.2 Delete `tests/ingestion/test_cli_migration.py`
- [ ] 5.3 Remove legacy CLI test fixtures
- [ ] 5.4 Update test configuration (remove legacy test markers)
- [ ] 5.5 Update CI config to not run legacy tests
- [ ] 5.6 Verify test suite still passes

## 6. Remove Migration Support Code

- [ ] 6.1 Remove flag translation functions
- [ ] 6.2 Remove migration warning formatters
- [ ] 6.3 Remove environment variable checks for migration
- [ ] 6.4 Clean up conditional logic for deprecated flags
- [ ] 6.5 Remove migration metrics collection code
- [ ] 6.6 Update error messages (no more "use new CLI" hints)

## 7. Simplify Unified CLI

- [ ] 7.1 Remove backward-compatible flag aliases (if no longer needed)
- [ ] 7.2 Simplify command parsing (no legacy translation)
- [ ] 7.3 Clean up error handling (remove migration hints)
- [ ] 7.4 Remove deprecation-related imports
- [ ] 7.5 Simplify help text (remove migration notices)
- [ ] 7.6 Run mypy --strict (ensure no type errors)

## 8. Update Documentation

- [ ] 8.1 Remove `docs/cli_migration_guide.md` (or move to archive)
- [ ] 8.2 Remove migration sections from `docs/ingestion_runbooks.md`
- [ ] 8.3 Update `README.md` to remove migration notices
- [ ] 8.4 Update `CHANGELOG.md` with breaking change notice
- [ ] 8.5 Update `docs/operations_manual.md` (remove legacy refs)
- [ ] 8.6 Clean up all "deprecated" notices in docs
- [ ] 8.7 Verify all code examples use unified CLI

## 9. Update Internal Tooling

- [ ] 9.1 Update internal scripts to remove legacy CLI usage
- [ ] 9.2 Update CI/CD pipelines (if any stragglers)
- [ ] 9.3 Update deployment scripts
- [ ] 9.4 Update monitoring/alerting configs
- [ ] 9.5 Update team runbooks
- [ ] 9.6 Notify internal users of removal

## 10. Prepare Release Notes

- [ ] 10.1 Draft release notes highlighting breaking change
- [ ] 10.2 List removed commands explicitly
- [ ] 10.3 Show before/after command examples
- [ ] 10.4 Link to unified CLI documentation
- [ ] 10.5 Emphasize this is a major version bump
- [ ] 10.6 Include rollback instructions

## 11. Testing and Validation

- [ ] 11.1 Run full test suite - all tests pass
- [ ] 11.2 Test package installation from scratch
- [ ] 11.3 Verify `med ingest` works correctly
- [ ] 11.4 Verify legacy commands return "command not found"
- [ ] 11.5 Test on multiple platforms (Linux, macOS, Windows)
- [ ] 11.6 Integration tests with real adapters
- [ ] 11.7 Performance check (ensure no regression)

## 12. Deployment Preparation

- [ ] 12.1 Bump major version number (e.g., 2.0.0)
- [ ] 12.2 Update version in all relevant files
- [ ] 12.3 Create release branch
- [ ] 12.4 Tag release
- [ ] 12.5 Build and verify package
- [ ] 12.6 Prepare rollback procedure

## 13. Communication

- [ ] 13.1 Send final migration deadline reminder (1 week before)
- [ ] 13.2 Publish blog post or announcement about removal
- [ ] 13.3 Update project website/docs
- [ ] 13.4 Post to relevant community channels (Slack, mailing list)
- [ ] 13.5 Update FAQ with "why was legacy CLI removed?"
- [ ] 13.6 Prepare support responses for migration questions

## 14. Deployment

- [ ] 14.1 Deploy to staging environment
- [ ] 14.2 Run smoke tests in staging
- [ ] 14.3 Verify legacy commands fail as expected
- [ ] 14.4 Monitor staging for 24-48 hours
- [ ] 14.5 Deploy to production (during low-traffic window)
- [ ] 14.6 Monitor error rates and user feedback

## 15. Post-Deployment

- [ ] 15.1 Monitor for issues in first 72 hours
- [ ] 15.2 Track support tickets related to removal
- [ ] 15.3 Update monitoring dashboards
- [ ] 15.4 Collect feedback from users
- [ ] 15.5 Document lessons learned
- [ ] 15.6 Archive migration metrics for retrospective
