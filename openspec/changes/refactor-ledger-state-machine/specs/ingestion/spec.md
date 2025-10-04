# Ledger State Machine

## MODIFIED Requirements

### Requirement: Ledger State Tracking

The ingestion ledger SHALL use an explicit state machine with validated transitions, replacing free-form string states.

#### Scenario: Type-safe state enumeration

- **WHEN** code references a ledger state
- **THEN** it SHALL use the `LedgerState` enum
- **AND** invalid state values SHALL be caught at compile time by mypy
- **AND** IDE autocomplete SHALL show all valid states

#### Scenario: State transition validation

- **WHEN** updating a document's state
- **THEN** the ledger SHALL validate the transition is allowed
- **WHEN** an invalid transition is attempted
- **THEN** the ledger SHALL raise `InvalidStateTransition` exception
- **AND** SHALL log the attempted transition for debugging

#### Scenario: Backwards-compatible string states

- **WHEN** legacy code passes string states (deprecated)
- **THEN** the ledger SHALL map strings to enum values
- **AND** SHALL emit deprecation warning
- **AND** SHALL function identically to enum usage

## ADDED Requirements

### Requirement: Ledger Compaction

The ledger SHALL support periodic compaction via snapshots and delta logs to maintain O(1) initialization time.

#### Scenario: Snapshot creation

- **WHEN** `create_snapshot()` is called
- **THEN** the ledger SHALL write full state to snapshot file
- **AND** SHALL include metadata (timestamp, document count, version)
- **AND** SHALL compress snapshot with gzip
- **AND** SHALL rotate old snapshots (keep last N)

#### Scenario: Loading from snapshot

- **WHEN** initializing ledger
- **THEN** it SHALL check for latest snapshot first
- **WHEN** snapshot exists
- **THEN** it SHALL load snapshot
- **AND** SHALL apply delta log entries
- **AND** initialization time SHALL be O(1) regardless of history length

#### Scenario: Automatic compaction

- **WHEN** ledger is active
- **THEN** it SHALL create snapshots automatically at configured interval
- **AND** SHALL truncate delta log after successful snapshot
- **AND** SHALL maintain snapshot rotation policy

### Requirement: Structured Audit Records

The ledger SHALL emit structured audit records with rich metadata for state changes.

#### Scenario: Complete audit trail

- **WHEN** a document state changes
- **THEN** the ledger SHALL write `LedgerAuditRecord` with full context
- **AND** SHALL include old_state, new_state, timestamp, adapter
- **WHEN** transition fails
- **THEN** audit record SHALL include error_type, error_message, traceback
- **WHEN** retrying
- **THEN** audit record SHALL include retry_count and max_retries

#### Scenario: Queryable audit records

- **WHEN** operators query the ledger
- **THEN** they CAN filter by error_type, adapter, state
- **AND** CAN aggregate durations by state
- **AND** CAN identify stuck documents by timestamp

### Requirement: State Machine Utilities

The ledger SHALL provide utility methods for common state machine operations.

#### Scenario: Valid transition discovery

- **WHEN** calling `get_valid_next_states(current_state)`
- **THEN** it SHALL return set of states reachable from current
- **AND** SHALL use transition graph for validation

#### Scenario: State classification

- **WHEN** calling `is_terminal_state(state)`
- **THEN** it SHALL return true for COMPLETED, FAILED, SKIPPED
- **WHEN** calling `is_retryable_state(state)`
- **THEN** it SHALL return true for states that allow retry transitions

#### Scenario: Stuck document detection

- **WHEN** calling `get_stuck_documents(threshold_hours)`
- **THEN** it SHALL return documents in non-terminal states longer than threshold
- **AND** SHALL include time stuck and current state
