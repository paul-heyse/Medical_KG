# Tasks: Remove Legacy Pipeline Wrappers

## 1. Audit Legacy Usage

- [ ] 1.1 Search codebase for all calls to `run_async_legacy()`
- [ ] 1.2 Search for `consumption_mode="run_async_legacy"` references
- [ ] 1.3 Grep for `MEDICAL_KG_SUPPRESS_PIPELINE_DEPRECATION` env variable
- [ ] 1.4 Check telemetry dashboards for legacy-specific counters
- [ ] 1.5 Review logs for deprecation warnings in staging/production
- [ ] 1.6 Document all remaining legacy usage patterns

## 2. Convert Remaining Callers

- [ ] 2.1 Identify internal services/scripts calling `run_async_legacy()`
- [ ] 2.2 Convert each caller to use `stream_events()` or `run_async()`
- [ ] 2.3 Test converted callers in isolation
- [ ] 2.4 Update integration tests for converted code paths
- [ ] 2.5 Deploy converted callers to staging
- [ ] 2.6 Monitor staging for any behavioral changes
- [ ] 2.7 Deploy to production and verify metrics

## 3. Remove Legacy Pipeline Methods

- [ ] 3.1 Delete `IngestionPipeline.run_async_legacy()` method
- [ ] 3.2 Delete `_log_legacy_usage()` helper function
- [ ] 3.3 Remove legacy consumption mode constants
- [ ] 3.4 Remove `_LEGACY_WARNING_ENV` constant
- [ ] 3.5 Clean up any legacy-specific error handling
- [ ] 3.6 Remove legacy method docstrings and examples
- [ ] 3.7 Run mypy strict on modified files

## 4. Clean Event System

- [ ] 4.1 Remove `consumption_mode="run_async_legacy"` parameter
- [ ] 4.2 Remove legacy mode tracking from `PipelineEvent` emissions
- [ ] 4.3 Update `PIPELINE_CONSUMPTION_COUNTER` to remove legacy label
- [ ] 4.4 Clean up event filtering that distinguished legacy mode
- [ ] 4.5 Remove any legacy-specific event transformers
- [ ] 4.6 Test event emission with all consumption modes removed
- [ ] 4.7 Verify event schema compatibility

## 5. Remove Environment Variables

- [ ] 5.1 Delete `MEDICAL_KG_SUPPRESS_PIPELINE_DEPRECATION` handling
- [ ] 5.2 Remove env variable checks from pipeline initialization
- [ ] 5.3 Update environment configuration documentation
- [ ] 5.4 Remove env variable from Docker/K8s configs
- [ ] 5.5 Clean up staging/production environment files
- [ ] 5.6 Update deployment scripts to remove legacy env vars
- [ ] 5.7 Verify no references remain in configuration management

## 6. Update Tests

- [ ] 6.1 Delete legacy test fixtures in `tests/ingestion/test_pipeline.py`
- [ ] 6.2 Remove `test_run_async_legacy_*` test functions
- [ ] 6.3 Remove deprecation warning assertion tests
- [ ] 6.4 Update fixtures that used legacy consumption mode
- [ ] 6.5 Ensure test coverage for `stream_events()` and `run_async()`
- [ ] 6.6 Run full test suite and verify all tests pass
- [ ] 6.7 Check test coverage hasn't decreased

## 7. Clean Telemetry and Metrics

- [ ] 7.1 Remove `PIPELINE_CONSUMPTION_COUNTER` legacy mode labels
- [ ] 7.2 Delete legacy-specific metrics from Prometheus config
- [ ] 7.3 Update Grafana dashboards to remove legacy panels
- [ ] 7.4 Remove legacy alerts from `ops/monitoring/prometheus-alerts.yaml`
- [ ] 7.5 Clean up metric names that reference "legacy"
- [ ] 7.6 Export updated dashboard JSON files
- [ ] 7.7 Deploy updated dashboards and verify metrics

## 8. Update Documentation

- [ ] 8.1 Remove legacy API examples from `docs/ingestion_runbooks.md`
- [ ] 8.2 Update migration guide to mark legacy path as removed
- [ ] 8.3 Remove "Deprecated" notices (method no longer exists)
- [ ] 8.4 Update API reference documentation
- [ ] 8.5 Remove legacy consumption mode from architecture diagrams
- [ ] 8.6 Update CONTRIBUTING.md to reference only streaming API
- [ ] 8.7 Add removal notice to CHANGELOG.md

## 9. Update Operations Guides

- [ ] 9.1 Remove legacy CLI examples from runbooks
- [ ] 9.2 Update troubleshooting guides to remove legacy references
- [ ] 9.3 Remove "if using legacy mode" conditionals
- [ ] 9.4 Update incident response playbooks
- [ ] 9.5 Clean up monitoring queries that filter by consumption mode
- [ ] 9.6 Update capacity planning docs (remove legacy overhead)
- [ ] 9.7 Refresh operational checklists

## 10. Communication and Rollout

- [ ] 10.1 Draft removal announcement for internal stakeholders
- [ ] 10.2 Notify teams that may have external integrations
- [ ] 10.3 Update release notes with breaking change notice
- [ ] 10.4 Create rollback procedure (restore from git if needed)
- [ ] 10.5 Schedule removal for major version increment
- [ ] 10.6 Deploy to staging with monitoring
- [ ] 10.7 Production deployment during maintenance window

## 11. Validation

- [ ] 11.1 Verify `grep -r "run_async_legacy"` returns no matches
- [ ] 11.2 Verify `grep -r "consumption_mode"` shows no legacy references
- [ ] 11.3 Confirm telemetry shows no legacy counter increments
- [ ] 11.4 Run full test suite - all tests pass
- [ ] 11.5 Run mypy strict on ingestion module - no errors
- [ ] 11.6 Check production logs for any unexpected errors
- [ ] 11.7 Monitor production metrics for 72 hours post-deployment

## 12. Final Cleanup

- [ ] 12.1 Archive any legacy-specific documentation
- [ ] 12.2 Remove legacy branches from version control
- [ ] 12.3 Update issue tracker to close legacy-related tickets
- [ ] 12.4 Document lessons learned from migration
- [ ] 12.5 Update project roadmap to reflect completion
- [ ] 12.6 Celebrate successful legacy code removal! 🎉
