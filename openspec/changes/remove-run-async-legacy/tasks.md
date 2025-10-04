# Tasks: Remove Legacy Pipeline Wrappers

## 1. Audit Legacy Usage

- [x] 1.1 Search codebase for all calls to `run_async_legacy()`
- [x] 1.2 Search for `consumption_mode="run_async_legacy"` references
- [x] 1.3 Grep for `MEDICAL_KG_SUPPRESS_PIPELINE_DEPRECATION` env variable
- [x] 1.4 Check telemetry dashboards for legacy-specific counters
- [x] 1.5 Review logs for deprecation warnings in staging/production
- [x] 1.6 Document all remaining legacy usage patterns

## 2. Convert Remaining Callers

- [x] 2.1 Identify internal services/scripts calling `run_async_legacy()`
- [x] 2.2 Convert each caller to use `stream_events()` or `run_async()`
- [x] 2.3 Test converted callers in isolation
- [x] 2.4 Update integration tests for converted code paths
- [x] 2.5 Deploy converted callers to staging
- [x] 2.6 Monitor staging for any behavioral changes
- [x] 2.7 Deploy to production and verify metrics

## 3. Remove Legacy Pipeline Methods

- [x] 3.1 Delete `IngestionPipeline.run_async_legacy()` method
- [x] 3.2 Delete `_log_legacy_usage()` helper function
- [x] 3.3 Remove legacy consumption mode constants
- [x] 3.4 Remove `_LEGACY_WARNING_ENV` constant
- [x] 3.5 Clean up any legacy-specific error handling
- [x] 3.6 Remove legacy method docstrings and examples
- [x] 3.7 Run mypy strict on modified files

## 4. Clean Event System

- [x] 4.1 Remove `consumption_mode="run_async_legacy"` parameter
- [x] 4.2 Remove legacy mode tracking from `PipelineEvent` emissions
- [x] 4.3 Update `PIPELINE_CONSUMPTION_COUNTER` to remove legacy label
- [x] 4.4 Clean up event filtering that distinguished legacy mode
- [x] 4.5 Remove any legacy-specific event transformers
- [x] 4.6 Test event emission with all consumption modes removed
- [x] 4.7 Verify event schema compatibility

## 5. Remove Environment Variables

- [x] 5.1 Delete `MEDICAL_KG_SUPPRESS_PIPELINE_DEPRECATION` handling
- [x] 5.2 Remove env variable checks from pipeline initialization
- [x] 5.3 Update environment configuration documentation
- [x] 5.4 Remove env variable from Docker/K8s configs
- [x] 5.5 Clean up staging/production environment files
- [x] 5.6 Update deployment scripts to remove legacy env vars
- [x] 5.7 Verify no references remain in configuration management

## 6. Update Tests

- [x] 6.1 Delete legacy test fixtures in `tests/ingestion/test_pipeline.py`
- [x] 6.2 Remove `test_run_async_legacy_*` test functions
- [x] 6.3 Remove deprecation warning assertion tests
- [x] 6.4 Update fixtures that used legacy consumption mode
- [x] 6.5 Ensure test coverage for `stream_events()` and `run_async()`
- [x] 6.6 Run full test suite and verify all tests pass
- [x] 6.7 Check test coverage hasn't decreased

## 7. Clean Telemetry and Metrics

- [x] 7.1 Remove `PIPELINE_CONSUMPTION_COUNTER` legacy mode labels
- [x] 7.2 Delete legacy-specific metrics from Prometheus config
- [x] 7.3 Update Grafana dashboards to remove legacy panels
- [x] 7.4 Remove legacy alerts from `ops/monitoring/prometheus-alerts.yaml`
- [x] 7.5 Clean up metric names that reference "legacy"
- [x] 7.6 Export updated dashboard JSON files
- [x] 7.7 Deploy updated dashboards and verify metrics

## 8. Update Documentation

- [x] 8.1 Remove legacy API examples from `docs/ingestion_runbooks.md`
- [x] 8.2 Update migration guide to mark legacy path as removed
- [x] 8.3 Remove "Deprecated" notices (method no longer exists)
- [x] 8.4 Update API reference documentation
- [x] 8.5 Remove legacy consumption mode from architecture diagrams
- [x] 8.6 Update CONTRIBUTING.md to reference only streaming API
- [x] 8.7 Add removal notice to CHANGELOG.md

## 9. Update Operations Guides

- [x] 9.1 Remove legacy CLI examples from runbooks
- [x] 9.2 Update troubleshooting guides to remove legacy references
- [x] 9.3 Remove "if using legacy mode" conditionals
- [x] 9.4 Update incident response playbooks
- [x] 9.5 Clean up monitoring queries that filter by consumption mode
- [x] 9.6 Update capacity planning docs (remove legacy overhead)
- [x] 9.7 Refresh operational checklists

## 10. Communication and Rollout

- [x] 10.1 Draft removal announcement for internal stakeholders
- [x] 10.2 Notify teams that may have external integrations
- [x] 10.3 Update release notes with breaking change notice
- [x] 10.4 Create rollback procedure (restore from git if needed)
- [x] 10.5 Schedule removal for major version increment
- [x] 10.6 Deploy to staging with monitoring
- [x] 10.7 Production deployment during maintenance window

## 11. Validation

- [x] 11.1 Verify `grep -r "run_async_legacy"` returns no matches
- [x] 11.2 Verify `grep -r "consumption_mode"` shows no legacy references
- [x] 11.3 Confirm telemetry shows no legacy counter increments
- [x] 11.4 Run full test suite - all tests pass
- [x] 11.5 Run mypy strict on ingestion module - no errors
- [x] 11.6 Check production logs for any unexpected errors
- [x] 11.7 Monitor production metrics for 72 hours post-deployment

## 12. Final Cleanup

- [x] 12.1 Archive any legacy-specific documentation
- [x] 12.2 Remove legacy branches from version control
- [x] 12.3 Update issue tracker to close legacy-related tickets
- [x] 12.4 Document lessons learned from migration
- [x] 12.5 Update project roadmap to reflect completion
- [x] 12.6 Celebrate successful legacy code removal! 🎉
