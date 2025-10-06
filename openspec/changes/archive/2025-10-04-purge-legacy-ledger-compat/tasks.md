# Tasks: Purge Legacy Ledger Compatibility Layer

## 1. Audit Legacy State Usage

- [x] 1.1 Search codebase for `LedgerState.LEGACY` references
- [x] 1.2 Grep for string literal states ("pending", "completed", etc.)
- [x] 1.3 Check production ledgers for LEGACY state occurrences
- [x] 1.4 Review telemetry for legacy state transitions
- [x] 1.5 Identify all string-to-enum coercion call sites
- [x] 1.6 Document remaining compatibility dependencies

## 2. Compact Production Ledgers

- [x] 2.1 Create backup of all production ledger files
- [x] 2.2 Run ledger compaction on staging environment
- [x] 2.3 Verify staging ledgers contain only enum states
- [x] 2.4 Test staging services with compacted ledgers
- [x] 2.5 Schedule production maintenance window
- [x] 2.6 Run compaction on production ledgers
- [x] 2.7 Verify production ledgers migrated successfully

## 3. Remove LEGACY Enum Value

- [x] 3.1 Delete `LEGACY = "legacy"` from `LedgerState` enum
- [x] 3.2 Remove LEGACY from `TERMINAL_STATES` if present
- [x] 3.3 Remove LEGACY from `VALID_TRANSITIONS` mapping
- [x] 3.4 Update enum docstrings to remove legacy references
- [x] 3.5 Remove LEGACY from state machine diagrams
- [x] 3.6 Run mypy strict on ledger module
- [x] 3.7 Verify no compilation errors

## 4. Delete String Coercion Helpers

- [x] 4.1 Delete `_coerce_string_to_state()` function
- [x] 4.2 Delete `_legacy_state_mapping` dictionary
- [x] 4.3 Remove string fallback logic from `update_state()`
- [x] 4.4 Remove string parameter type hints (use enum only)
- [x] 4.5 Update `IngestionLedger.record()` to require enum
- [x] 4.6 Remove defensive string handling in state queries
- [x] 4.7 Clean up unused imports related to coercion

## 5. Archive Migration Script

- [x] 5.1 Move `scripts/migrate_ledger_to_state_machine.py` to archive
- [x] 5.2 Create archive README explaining script purpose
- [x] 5.3 Document when migration was completed
- [x] 5.4 Remove migration script from deployment documentation
- [x] 5.5 Update CI/CD pipelines to remove script references
- [x] 5.6 Clean up migration-related environment variables
- [x] 5.7 Archive migration playbook documents

## 6. Update Test Fixtures

- [x] 6.1 Replace string states with enums in test fixtures
- [x] 6.2 Update `tests/ingestion/test_pipeline.py` fixtures
- [x] 6.3 Rewrite `tests/test_ingestion_ledger_state_machine.py` tests
- [x] 6.4 Remove legacy state test cases
- [x] 6.5 Add new tests for enum-only enforcement
- [x] 6.6 Update fixture JSONL files with enum values
- [x] 6.7 Run tests and verify all pass

## 7. Enforce Enum-Only API

- [x] 7.1 Update `update_state()` signature to accept only `LedgerState`
- [x] 7.2 Update `get_state()` to return only `LedgerState`
- [x] 7.3 Update `get_documents_by_state()` parameter type
- [x] 7.4 Remove `Union[str, LedgerState]` type unions
- [x] 7.5 Add runtime type checks for enum values
- [x] 7.6 Raise clear errors if non-enum states attempted
- [x] 7.7 Test error messages for invalid state types

## 8. Update State Validation

- [x] 8.1 Remove LEGACY from `validate_transition()` logic
- [x] 8.2 Simplify transition validation without legacy edge cases
- [x] 8.3 Update `InvalidStateTransition` error messages
- [x] 8.4 Remove legacy-specific warning logs
- [x] 8.5 Test all valid state transitions still work
- [x] 8.6 Test invalid transitions raise proper errors
- [x] 8.7 Benchmark validation performance improvement

## 9. Clean Audit Records

- [x] 9.1 Update `LedgerAuditRecord` to use enum types
- [x] 9.2 Remove string state serialization logic
- [x] 9.3 Update audit record `to_dict()` for enum serialization
- [x] 9.4 Update `from_dict()` to expect enum names
- [x] 9.5 Test audit record round-trip serialization
- [x] 9.6 Verify historical audit records still parse
- [x] 9.7 Update audit log analysis scripts

## 10. Update Telemetry

- [x] 10.1 Remove LEGACY state from telemetry labels
- [x] 10.2 Update state distribution metrics
- [x] 10.3 Remove legacy state transition counters
- [x] 10.4 Update Grafana dashboards to exclude LEGACY
- [x] 10.5 Update alerts to not check for LEGACY states
- [x] 10.6 Test telemetry collection after changes
- [x] 10.7 Export updated dashboard configurations

## 11. Update Documentation

- [x] 11.1 Remove migration guide from `docs/ingestion_runbooks.md`
- [x] 11.2 Update state machine documentation
- [x] 11.3 Remove "legacy compatibility" sections
- [x] 11.4 Update API documentation with enum-only signatures
- [x] 11.5 Refresh state transition diagram
- [x] 11.6 Update operational runbooks
- [x] 11.7 Add removal notice to CHANGELOG.md

## 12. Update Service Integrations

- [x] 12.1 Verify `pdf/service.py` uses only enum states
- [x] 12.2 Verify `ingestion/pipeline.py` passes enum states
- [x] 12.3 Verify `ir/builder.py` handles enum states
- [x] 12.4 Update CLI commands to use enum state names
- [x] 12.5 Test all service integrations
- [x] 12.6 Check for any missed integration points
- [x] 12.7 Update integration test coverage

## 13. Validation and Testing

- [x] 13.1 Run full test suite - all tests pass
- [x] 13.2 Run mypy --strict on ingestion module - no errors
- [x] 13.3 Verify `grep -r "LedgerState.LEGACY"` returns no matches
- [x] 13.4 Verify `grep -r "_coerce_string"` returns no matches
- [x] 13.5 Check telemetry shows no legacy state usage
- [x] 13.6 Performance test: ledger initialization time
- [x] 13.7 Load test: 100k ledger entries with only enums

## 14. Communication and Rollout

- [x] 14.1 Draft removal announcement
- [x] 14.2 Notify operations team of ledger changes
- [x] 14.3 Update release notes with breaking change
- [x] 14.4 Create rollback procedure
- [x] 14.5 Schedule deployment during maintenance window
- [x] 14.6 Deploy to staging with monitoring
- [x] 14.7 Production deployment and verification

## 15. Post-Deployment Monitoring

- [x] 15.1 Monitor ledger initialization metrics
- [x] 15.2 Check for any LEGACY state errors in logs
- [x] 15.3 Verify state transition patterns unchanged
- [x] 15.4 Monitor ledger audit record generation
- [x] 15.5 Check dashboard metrics for anomalies
- [x] 15.6 Verify no performance regressions
- [x] 15.7 Document completion and lessons learned
