# Tasks: Remove Legacy Ingestion Tooling

## 1. Audit Tooling Usage

- [ ] 1.1 List all files in `scripts/cli_migration/`
- [ ] 1.2 Search for references to migration scripts in docs
- [ ] 1.3 Check CI/CD pipelines for migration script usage
- [ ] 1.4 Grep for legacy CLI command examples
- [ ] 1.5 Review operations guides for outdated commands
- [ ] 1.6 Document all tooling to be removed

## 2. Verify Migration Complete

- [ ] 2.1 Check CLI adoption metrics (confirm >95%)
- [ ] 2.2 Verify no legacy CLI usage in production logs
- [ ] 2.3 Confirm unified CLI handles all use cases
- [ ] 2.4 Review with stakeholders that migration is complete
- [ ] 2.5 Document migration completion date
- [ ] 2.6 Archive final migration status report
- [ ] 2.7 Get approval to proceed with tooling removal

## 3. Delete Migration Scripts

- [ ] 3.1 Delete `scripts/cli_migration/` directory
- [ ] 3.2 Delete `scripts/check_streaming_migration.py`
- [ ] 3.3 Delete `scripts/validate_cli_migration.py`
- [ ] 3.4 Remove migration helper functions from `scripts/utils.py`
- [ ] 3.5 Clean up any migration-related imports
- [ ] 3.6 Verify scripts directory cleaned up
- [ ] 3.7 Update scripts README if present

## 4. Archive Migration Documentation

- [ ] 4.1 Move `CLI_UNIFICATION_ROADMAP.md` to `docs/archive/`
- [ ] 4.2 Move `CLI_UNIFICATION_SUMMARY.md` to `docs/archive/`
- [ ] 4.3 Add "ARCHIVED" header to moved documents
- [ ] 4.4 Document completion date in archived files
- [ ] 4.5 Create archive index explaining historical context
- [ ] 4.6 Link to archive from main documentation
- [ ] 4.7 Update documentation index

## 5. Remove Legacy CLI References

- [ ] 5.1 Remove legacy examples from `docs/operations_manual.md`
- [ ] 5.2 Remove legacy commands from `docs/ingestion_runbooks.md`
- [ ] 5.3 Update CLI reference documentation
- [ ] 5.4 Remove "deprecated command" warnings
- [ ] 5.5 Update troubleshooting guides
- [ ] 5.6 Clean up command comparison tables
- [ ] 5.7 Verify only unified CLI documented

## 6. Update Operations Guides

- [ ] 6.1 Rewrite runbook examples to use unified CLI only
- [ ] 6.2 Remove "if using legacy CLI" conditionals
- [ ] 6.3 Update incident response playbooks
- [ ] 6.4 Refresh capacity planning docs
- [ ] 6.5 Update monitoring query examples
- [ ] 6.6 Clean up operational checklists
- [ ] 6.7 Test operations guides with unified CLI

## 7. Remove Environment Variables

- [ ] 7.1 Delete `MEDICAL_KG_CLI_MIGRATION_MODE` handling
- [ ] 7.2 Remove `MEDICAL_KG_LEGACY_CLI_WARNING` variable
- [ ] 7.3 Clean up migration-related environment checks
- [ ] 7.4 Remove env vars from Docker/K8s configs
- [ ] 7.5 Update environment documentation
- [ ] 7.6 Clean up `.env.example` files
- [ ] 7.7 Verify no orphaned env variable references

## 8. Update CI/CD Pipelines

- [ ] 8.1 Remove legacy CLI test jobs from `.github/workflows/`
- [ ] 8.2 Delete CLI migration validation steps
- [ ] 8.3 Remove legacy CLI integration tests
- [ ] 8.4 Update test matrix to use unified CLI only
- [ ] 8.5 Clean up test fixtures for legacy CLI
- [ ] 8.6 Verify CI runs cleanly without legacy tests
- [ ] 8.7 Update CI documentation

## 9. Update Contributor Guides

- [ ] 9.1 Remove legacy CLI sections from CONTRIBUTING.md
- [ ] 9.2 Update development setup to reference unified CLI
- [ ] 9.3 Remove migration guidance for contributors
- [ ] 9.4 Update testing instructions
- [ ] 9.5 Refresh CLI development patterns
- [ ] 9.6 Update code review guidelines
- [ ] 9.7 Add link to archived migration docs

## 10. Update Release Checklist

- [ ] 10.1 Remove CLI migration validation from release checklist
- [ ] 10.2 Remove legacy CLI compatibility checks
- [ ] 10.3 Update release notes template
- [ ] 10.4 Remove migration announcement sections
- [ ] 10.5 Clean up rollback procedures
- [ ] 10.6 Update deployment verification steps
- [ ] 10.7 Refresh release documentation

## 11. Clean Test Fixtures

- [ ] 11.1 Remove legacy CLI test fixtures
- [ ] 11.2 Delete migration verification tests
- [ ] 11.3 Update CLI integration test suite
- [ ] 11.4 Remove legacy command mocks
- [ ] 11.5 Clean up test helper functions
- [ ] 11.6 Run test suite - verify all pass
- [ ] 11.7 Check test coverage maintained

## 12. Update Project Documentation

- [ ] 12.1 Update README.md with unified CLI examples only
- [ ] 12.2 Refresh quick start guide
- [ ] 12.3 Update installation documentation
- [ ] 12.4 Remove migration timeline from project docs
- [ ] 12.5 Update architectural diagrams
- [ ] 12.6 Refresh API documentation
- [ ] 12.7 Add removal notice to CHANGELOG.md

## 13. Validation

- [ ] 13.1 Verify `grep -r "cli_migration"` returns no matches
- [ ] 13.2 Verify `grep -r "legacy.*cli"` limited to archives
- [ ] 13.3 Check all docs reference unified CLI only
- [ ] 13.4 Run full test suite - all tests pass
- [ ] 13.5 Verify CI pipelines run successfully
- [ ] 13.6 Check for any broken documentation links
- [ ] 13.7 Test unified CLI covers all documented use cases

## 14. Communication and Rollout

- [ ] 14.1 Announce tooling removal in team channels
- [ ] 14.2 Update project status dashboard
- [ ] 14.3 Notify documentation team of changes
- [ ] 14.4 Update issue tracker (close migration tickets)
- [ ] 14.5 Archive migration-related issues
- [ ] 14.6 Update project roadmap
- [ ] 14.7 Document completion and celebrate! 🎉
