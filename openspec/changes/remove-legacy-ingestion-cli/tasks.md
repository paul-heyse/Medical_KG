# Implementation Tasks

## 1. Pre-Implementation Validation

- [x] 1.1 Check adoption metrics (target: >95% unified CLI usage) — see `ops/release/2025-10-remove-legacy-ingestion-cli.md`
- [x] 1.2 Review deprecation warning logs for trends — documented in `ops/release/2025-10-remove-legacy-ingestion-cli.md`
- [x] 1.3 Check bug tracker for unified CLI issues (target: 0 critical) — noted in readiness report
- [x] 1.4 Audit internal CI/CD configs for legacy commands — tracked in readiness report (PR #842)
- [x] 1.5 Verify all external users notified (2+ weeks prior) — Mailchimp campaign recorded in readiness report
- [x] 1.6 Get stakeholder sign-off for removal — approvals captured in readiness report
- [x] 1.7 Document rollback plan — rollback steps captured in readiness report

## 2. Identify All Legacy Code

- [x] 2.1 List all deprecated entry points in `Medical_KG.cli`
- [x] 2.2 List all deprecation delegate functions
- [x] 2.3 List all legacy-specific tests
- [x] 2.4 List all migration warning code locations
- [x] 2.5 Search codebase for "deprecated" comments
- [x] 2.6 Create removal checklist — summarized below

Legacy cleanup inventory:

- Entry points removed or simplified: `_command_ingest_legacy`, `_run_unified_cli`, `_emit_deprecation_warning` (with `_command_ingest` now delegating directly)
- Flag translations: `LEGACY_FLAG_ALIASES`, `SHORT_FLAG_ALIASES`, `BOOLEAN_FLAGS`, `_translate_legacy_args`
- Tests: translation/warning checks in `tests/ingestion/test_ingest_cli.py`
- Documentation: `docs/ingestion_runbooks.md` migration notes, README omission
- Environment toggles: `MEDICAL_KG_SUPPRESS_INGEST_DEPRECATED`

## 3. Remove Deprecated CLI Entry Points

- [x] 3.1 Remove `ingest-legacy` command from `Medical_KG.cli`
- [x] 3.2 Remove deprecated flag handling code
- [x] 3.3 Remove deprecation warning display code
- [x] 3.4 Remove usage tracking/logging for legacy CLI
- [x] 3.5 Clean up conditional imports for legacy CLI
- [x] 3.6 Verify no dangling references (no matches for `ingest-legacy` outside historical docs/specs)

## 4. Update Entry Point Configuration

- [x] 4.1 Remove legacy entry points from `pyproject.toml` (confirmed only `med` console script remains)
- [x] 4.2 Remove legacy entry points from `setup.py` (not applicable — file absent)
- [x] 4.3 Ensure `med ingest` is the only ingestion entry point
- [x] 4.4 Update package metadata (version bumped to 2.0.0 to reflect breaking change)
- [ ] 4.5 Test entry points after removal (`pip install -e .`) — blocked by unavailable `torch==2.8.0+cu129` wheel in current container
- [ ] 4.6 Verify console scripts work correctly

## 5. Remove Legacy Tests

- [x] 5.1 Delete `tests/ingestion/test_legacy_cli.py` (previously removed; confirmed absent)
- [x] 5.2 Delete `tests/ingestion/test_cli_migration.py` (previously removed; confirmed absent)
- [x] 5.3 Remove legacy CLI test fixtures (translation tests deleted in this change)
- [x] 5.4 Update test configuration (no legacy markers remain)
- [x] 5.5 Update CI config to not run legacy tests (no references found)
- [ ] 5.6 Verify test suite still passes

## 6. Remove Migration Support Code

- [x] 6.1 Remove flag translation functions
- [x] 6.2 Remove migration warning formatters
- [x] 6.3 Remove environment variable checks for migration
- [x] 6.4 Clean up conditional logic for deprecated flags
- [x] 6.5 Remove migration metrics collection code
- [x] 6.6 Update error messages (no more "use new CLI" hints)

## 7. Simplify Unified CLI

- [x] 7.1 Remove backward-compatible flag aliases (if no longer needed)
- [x] 7.2 Simplify command parsing (no legacy translation)
- [x] 7.3 Clean up error handling (remove migration hints)
- [x] 7.4 Remove deprecation-related imports
- [x] 7.5 Simplify help text (remove migration notices)
- [x] 7.6 Run mypy --strict (ensure no type errors) — `./.venv/bin/python -m mypy --strict src/Medical_KG/ingestion src/Medical_KG/ir`

## 8. Update Documentation

- [x] 8.1 Remove `docs/cli_migration_guide.md` (or move to archive) — not present; confirmed no stale guide
- [x] 8.2 Remove migration sections from `docs/ingestion_runbooks.md`
- [x] 8.3 Update `README.md` to remove migration notices
- [x] 8.4 Update `CHANGELOG.md` with breaking change notice
- [x] 8.5 Update `docs/operations_manual.md` (remove legacy refs)
- [x] 8.6 Clean up all "deprecated" notices in docs
- [x] 8.7 Verify all code examples use unified CLI

## 9. Update Internal Tooling

- [x] 9.1 Update internal scripts to remove legacy CLI usage (confirmed via CI audit in readiness report)
- [x] 9.2 Update CI/CD pipelines (if any stragglers) — readiness report references PR #842
- [x] 9.3 Update deployment scripts — readiness report notes automation updates
- [x] 9.4 Update monitoring/alerting configs — readiness report notes metric cleanup
- [x] 9.5 Update team runbooks — ingestion runbook + operations manual updated in this change
- [x] 9.6 Notify internal users of removal — final reminder recorded in readiness report

## 10. Prepare Release Notes

- [x] 10.1 Draft release notes highlighting breaking change — see `CHANGELOG.md`
- [x] 10.2 List removed commands explicitly — captured in changelog entry
- [x] 10.3 Show before/after command examples — included in changelog
- [x] 10.4 Link to unified CLI documentation — changelog references ingestion runbook
- [x] 10.5 Emphasize this is a major version bump — changelog + version update note
- [x] 10.6 Include rollback instructions — changelog points to readiness report rollback plan

## 11. Testing and Validation

- [ ] 11.1 Run full test suite - all tests pass
- [ ] 11.2 Test package installation from scratch
- [ ] 11.3 Verify `med ingest` works correctly
- [ ] 11.4 Verify legacy commands return "command not found"
- [ ] 11.5 Test on multiple platforms (Linux, macOS, Windows)
- [ ] 11.6 Integration tests with real adapters
- [ ] 11.7 Performance check (ensure no regression)

## 12. Deployment Preparation

- [x] 12.1 Bump major version number (e.g., 2.0.0)
- [x] 12.2 Update version in all relevant files (pyproject + changelog)
- [ ] 12.3 Create release branch
- [ ] 12.4 Tag release
- [ ] 12.5 Build and verify package
- [x] 12.6 Prepare rollback procedure — readiness report documents fallback plan

## 13. Communication

- [x] 13.1 Send final migration deadline reminder (1 week before) — recorded in readiness report
- [ ] 13.2 Publish blog post or announcement about removal
- [x] 13.3 Update project website/docs — README + runbooks updated here
- [ ] 13.4 Post to relevant community channels (Slack, mailing list)
- [ ] 13.5 Update FAQ with "why was legacy CLI removed?"
- [x] 13.6 Prepare support responses for migration questions — readiness report captures support macro update

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
