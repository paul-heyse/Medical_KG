# Spec Delta: Ingestion Ledger (purge-legacy-ledger-compat)

## REMOVED Requirements

### Requirement: Legacy State Enum Value

**Reason**: All production ledgers migrated to enum-based format

**Migration**: Run ledger compaction to convert remaining LEGACY markers to appropriate enum values

The `LedgerState.LEGACY` enum value was a placeholder during the state machine migration to handle string-based states from historical ledgers.

### Requirement: String-to-Enum Coercion

**Reason**: No longer needed after full enum adoption

**Migration**: Update all code to use `LedgerState` enum values directly

String coercion helpers mapped arbitrary string states to enum values during boot-time translation.

### Requirement: Legacy State Migration Tooling

**Reason**: One-time migration completed

**Migration**: N/A - migration script archived for historical reference

The migration script (`migrate_ledger_to_state_machine.py`) converted string-based ledgers to enum format.

## MODIFIED Requirements

### Requirement: Ledger State Machine

The ingestion ledger SHALL enforce state transitions using an explicit `LedgerState` enum without legacy compatibility layers.

**Modifications**:

- Removed `LEGACY` enum value
- Eliminated string-to-enum coercion
- Enforced enum-only API surface

#### Scenario: Update ledger state with enum

- **GIVEN** a ledger entry in `PENDING` state
- **WHEN** `update_state(doc_id, LedgerState.PROCESSING)` is called
- **THEN** the state transitions to `PROCESSING`
- **AND** no string coercion is performed
- **AND** the transition is validated against `VALID_TRANSITIONS`

#### Scenario: Query documents by enum state

- **GIVEN** multiple ledger entries with various states
- **WHEN** `get_documents_by_state(LedgerState.COMPLETED)` is called
- **THEN** only completed documents are returned
- **AND** no LEGACY state filtering is performed

#### Scenario: Reject string state values

- **GIVEN** code attempting to use string states
- **WHEN** `update_state(doc_id, "completed")` is called with a string
- **THEN** a `TypeError` is raised at runtime (if not caught by mypy)
- **AND** the error message suggests using `LedgerState.COMPLETED` enum

#### Scenario: Ledger initialization without coercion

- **GIVEN** a ledger file containing only enum-based states
- **WHEN** the ledger is loaded
- **THEN** initialization completes in O(1) time
- **AND** no string-to-enum translation is performed
- **AND** all states are valid `LedgerState` enum members

### Requirement: Ledger Audit Trail

The ingestion ledger SHALL generate structured audit records using enum states for all transitions.

**Modifications**:

- Removed LEGACY state from audit record schema
- Simplified audit record serialization (no string coercion)

#### Scenario: Audit record contains enum states

- **GIVEN** a state transition from `PENDING` to `COMPLETED`
- **WHEN** an audit record is created
- **THEN** `old_state` is `LedgerState.PENDING`
- **AND** `new_state` is `LedgerState.COMPLETED`
- **AND** no LEGACY state markers are present
- **AND** serialization uses enum names ("PENDING", "COMPLETED")

### Requirement: Ledger State Validation

The ingestion ledger SHALL validate all state transitions against an explicit transition map without legacy exceptions.

**Modifications**:

- Removed LEGACY state from `VALID_TRANSITIONS` mapping
- Simplified validation logic

#### Scenario: Validate transition without legacy cases

- **GIVEN** a transition from `PENDING` to `PROCESSING`
- **WHEN** `validate_transition()` is called
- **THEN** the transition is validated against `VALID_TRANSITIONS`
- **AND** no special legacy transition rules are applied
- **AND** validation passes for allowed transitions only
