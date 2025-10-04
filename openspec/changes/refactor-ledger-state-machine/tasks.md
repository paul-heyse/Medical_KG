# Implementation Tasks

## 1. Design State Machine

- [ ] 1.1 Define `LedgerState` enum with all valid states
- [ ] 1.2 Map existing string states to enum values (audit current usage)
- [ ] 1.3 Define `VALID_TRANSITIONS` dict mapping each state to allowed next states
- [ ] 1.4 Add `TERMINAL_STATES` set (COMPLETED, FAILED, SKIPPED)
- [ ] 1.5 Add `RETRYABLE_STATES` set (states that can transition to RETRYING)
- [ ] 1.6 Document state machine with transition diagram
- [ ] 1.7 Add comprehensive docstrings explaining each state's meaning

## 2. Implement State Machine Validation

- [ ] 2.1 Create `validate_transition(old: LedgerState, new: LedgerState)` function
- [ ] 2.2 Raise `InvalidStateTransition` exception for invalid transitions
- [ ] 2.3 Add transition validation to `Ledger.update_state()` method
- [ ] 2.4 Log all state transitions with old/new states
- [ ] 2.5 Add metrics counter for state transitions by type
- [ ] 2.6 Test all valid transitions pass validation
- [ ] 2.7 Test all invalid transitions raise exception

## 3. Create Structured Audit Records

- [ ] 3.1 Define `LedgerAuditRecord` dataclass
- [ ] 3.2 Add fields: doc_id, old_state, new_state, timestamp, adapter
- [ ] 3.3 Add error metadata: error_type, error_message, traceback
- [ ] 3.4 Add context metadata: retry_count, duration, parameters
- [ ] 3.5 Implement `to_dict()` for JSONL serialization
- [ ] 3.6 Implement `from_dict()` for deserialization
- [ ] 3.7 Add comprehensive type hints for all fields

## 4. Refactor Ledger Core

- [ ] 4.1 Update `Ledger.__init__()` to use state machine
- [ ] 4.2 Replace string state comparisons with enum comparisons
- [ ] 4.3 Update `update_state()` to accept `LedgerState` enum
- [ ] 4.4 Update `get_state()` to return `LedgerState` enum
- [ ] 4.5 Add `get_documents_by_state(state: LedgerState)` method
- [ ] 4.6 Add backwards compatibility layer for string states (deprecated)
- [ ] 4.7 Emit deprecation warnings when string states are used

## 5. Implement Compaction System

- [ ] 5.1 Design snapshot format (JSON with metadata + state dict)
- [ ] 5.2 Implement `create_snapshot(output_path: Path)` method
- [ ] 5.3 Implement `load_snapshot(snapshot_path: Path)` method
- [ ] 5.4 Implement delta log format (JSONL of changes since snapshot)
- [ ] 5.5 Add `load_with_compaction(snapshot_path, delta_path)` method
- [ ] 5.6 Add automatic snapshot creation (configurable interval, default daily)
- [ ] 5.7 Add snapshot rotation (keep last N snapshots, default 7)
- [ ] 5.8 Add delta log truncation after successful snapshot

## 6. Update Initialization Logic

- [ ] 6.1 Check for snapshot file first during initialization
- [ ] 6.2 Load snapshot if present, else load full JSONL
- [ ] 6.3 Apply delta log entries on top of snapshot
- [ ] 6.4 Benchmark initialization time with snapshot vs full load
- [ ] 6.5 Add metrics for initialization method (snapshot vs full)
- [ ] 6.6 Add metrics for initialization duration
- [ ] 6.7 Document initialization process in runbook

## 7. Create Migration Script

- [ ] 7.1 Create `scripts/migrate_ledger_to_state_machine.py`
- [ ] 7.2 Parse existing JSONL ledger
- [ ] 7.3 Map string states to enum values (with fallback to LEGACY)
- [ ] 7.4 Validate transitions in historical data (log warnings)
- [ ] 7.5 Write new ledger with enum states
- [ ] 7.6 Create backup of original ledger
- [ ] 7.7 Add dry-run mode for validation without modification
- [ ] 7.8 Add progress reporting for large ledgers
- [ ] 7.9 Add validation that migrated ledger loads correctly
- [ ] 7.10 Document migration process in runbook

## 8. Update Service Integrations

- [ ] 8.1 Update `pdf/service.py` to use `LedgerState` enum
- [ ] 8.2 Update `ingestion/pipeline.py` to use enum states
- [ ] 8.3 Update `ir/builder.py` to use enum states
- [ ] 8.4 Replace all hardcoded state strings with enum references
- [ ] 8.5 Add type checking to ensure no string states remain
- [ ] 8.6 Update CLI commands to accept enum state names
- [ ] 8.7 Test all service integrations with new state machine

## 9. Add State Machine Utilities

- [ ] 9.1 Add `get_valid_next_states(current: LedgerState)` helper
- [ ] 9.2 Add `is_terminal_state(state: LedgerState)` helper
- [ ] 9.3 Add `is_retryable_state(state: LedgerState)` helper
- [ ] 9.4 Add `get_state_duration(doc_id: str)` method
- [ ] 9.5 Add `get_state_history(doc_id: str)` method
- [ ] 9.6 Add `get_stuck_documents(threshold_hours: int)` method
- [ ] 9.7 Document utility functions in API reference

## 10. Enhance Error Handling

- [ ] 10.1 Create `LedgerError` exception base class
- [ ] 10.2 Create `InvalidStateTransition` exception
- [ ] 10.3 Create `LedgerCorruption` exception
- [ ] 10.4 Add error recovery for corrupted state transitions
- [ ] 10.5 Log all exceptions with structured context
- [ ] 10.6 Add alerting for critical ledger errors
- [ ] 10.7 Document error handling patterns

## 11. Add Comprehensive Tests

- [ ] 11.1 Test all valid state transitions
- [ ] 11.2 Test all invalid transitions raise exceptions
- [ ] 11.3 Test state machine with realistic workflows
- [ ] 11.4 Test audit record serialization/deserialization
- [ ] 11.5 Test snapshot creation and loading
- [ ] 11.6 Test delta log application
- [ ] 11.7 Test compaction reduces initialization time
- [ ] 11.8 Test migration script with sample data
- [ ] 11.9 Test backwards compatibility with string states
- [ ] 11.10 Test concurrent state updates
- [ ] 11.11 Integration test with real pipeline
- [ ] 11.12 Performance test: 1M entries with compaction

## 12. Add Monitoring and Observability

- [ ] 12.1 Add Prometheus metrics for state distribution
- [ ] 12.2 Track state transition counts by type
- [ ] 12.3 Track documents stuck in non-terminal states
- [ ] 12.4 Track average time in each state
- [ ] 12.5 Add alerts for unusual state patterns
- [ ] 12.6 Create Grafana dashboard for ledger health
- [ ] 12.7 Document metrics in operations manual

## 13. Update Documentation

- [ ] 13.1 Document state machine in `docs/ingestion_runbooks.md`
- [ ] 13.2 Add state transition diagram
- [ ] 13.3 Document each state's meaning and typical duration
- [ ] 13.4 Document compaction mechanism
- [ ] 13.5 Add troubleshooting guide for stuck states
- [ ] 13.6 Document migration process
- [ ] 13.7 Add examples of querying ledger by state
- [ ] 13.8 Update API documentation

## 14. Create Operational Tooling

- [ ] 14.1 Add `med ledger compact` CLI command
- [ ] 14.2 Add `med ledger validate` CLI command (check transitions)
- [ ] 14.3 Add `med ledger stats` CLI command (state distribution)
- [ ] 14.4 Add `med ledger stuck` CLI command (find stuck documents)
- [ ] 14.5 Add `med ledger history <doc_id>` CLI command
- [ ] 14.6 Add `med ledger migrate` CLI command wrapper
- [ ] 14.7 Document all CLI commands in runbook

## 15. Validation and Rollout

- [ ] 15.1 Run full test suite - all tests pass
- [ ] 15.2 Run mypy --strict - no type errors
- [ ] 15.3 Validate migration script on production copy
- [ ] 15.4 Benchmark compaction on large ledgers (100k+ entries)
- [ ] 15.5 Test snapshot/restore cycle
- [ ] 15.6 Deploy to staging with gradual rollout
- [ ] 15.7 Monitor state transition patterns
- [ ] 15.8 Migrate production ledgers during maintenance window
- [ ] 15.9 Validate production after migration
- [ ] 15.10 Post-deployment monitoring (7 days)
