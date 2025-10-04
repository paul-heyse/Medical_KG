from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from Medical_KG.ingestion.ledger import (
    IngestionLedger,
    InvalidStateTransition,
    LedgerAuditRecord,
    LedgerState,
    get_valid_next_states,
    is_retryable_state,
    is_terminal_state,
    validate_transition,
)


def test_validate_transition_accepts_declared_edges() -> None:
    for state in (
        LedgerState.PENDING,
        LedgerState.FETCHING,
        LedgerState.FETCHED,
        LedgerState.PARSING,
        LedgerState.PARSED,
        LedgerState.VALIDATING,
        LedgerState.VALIDATED,
        LedgerState.IR_BUILDING,
        LedgerState.IR_READY,
        LedgerState.EMBEDDING,
        LedgerState.INDEXED,
        LedgerState.RETRYING,
    ):
        for successor in get_valid_next_states(state):
            validate_transition(state, successor)


def test_validate_transition_rejects_invalid_edge() -> None:
    with pytest.raises(InvalidStateTransition):
        validate_transition(LedgerState.FETCHING, LedgerState.IR_READY)


def test_audit_record_round_trip() -> None:
    record = LedgerAuditRecord(
        doc_id="doc-1",
        old_state=LedgerState.FETCHING,
        new_state=LedgerState.FETCHED,
        timestamp=datetime.now(timezone.utc).timestamp(),
        adapter="stub",
        metadata={"key": "value"},
        parameters={"attempt": 1},
        retry_count=2,
        duration_seconds=0.5,
    )
    payload = record.to_dict()
    assert payload["old_state"] == "FETCHING"
    assert payload["new_state"] == "FETCHED"
    restored = LedgerAuditRecord.from_dict(record.to_dict())
    assert restored.doc_id == record.doc_id
    assert restored.new_state is LedgerState.FETCHED
    assert restored.metadata == record.metadata
    assert restored.parameters == record.parameters


def test_snapshot_round_trip(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = IngestionLedger(ledger_path, auto_snapshot_interval=timedelta(days=7))
    ledger.update_state("doc-1", LedgerState.FETCHING)
    ledger.update_state("doc-1", LedgerState.FETCHED)
    snapshot = ledger.create_snapshot()
    assert snapshot.exists()
    assert ledger_path.read_text(encoding="utf-8") == ""
    reloaded = IngestionLedger(ledger_path)
    state = reloaded.get("doc-1")
    assert state is not None
    assert state.state is LedgerState.FETCHED


def test_stuck_documents_detection(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl", auto_snapshot_interval=timedelta(days=7))
    ledger.update_state("doc-stuck", LedgerState.FETCHING)
    document = ledger.get("doc-stuck")
    assert document is not None
    document.updated_at = datetime.now(timezone.utc) - timedelta(hours=5)
    stuck = ledger.get_stuck_documents(threshold_hours=1)
    assert stuck and stuck[0].doc_id == "doc-stuck"


def test_update_state_rejects_string_values(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    with pytest.raises(TypeError) as excinfo:
        ledger.update_state("doc-1", "completed")  # type: ignore[arg-type]
    assert "LedgerState enum" in str(excinfo.value)


def test_record_requires_enum(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    with pytest.raises(TypeError) as excinfo:
        ledger.record("doc-1", "completed")  # type: ignore[arg-type]
    assert "LedgerState enum" in str(excinfo.value)


def test_legacy_alias_entries_still_parse(tmp_path: Path) -> None:
    ledger_path = tmp_path / "legacy.jsonl"
    timestamp = datetime.now(timezone.utc).timestamp()
    ledger_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "doc_id": "doc-1",
                        "old_state": "legacy",
                        "new_state": "pdf_ir_ready",
                        "timestamp": timestamp,
                        "adapter": "stub",
                        "metadata": {},
                        "parameters": {},
                    }
                ),
                json.dumps(
                    {
                        "doc_id": "doc-1",
                        "old_state": "IR_READY",
                        "new_state": "COMPLETED",
                        "timestamp": timestamp + 1,
                        "adapter": "stub",
                        "metadata": {},
                        "parameters": {},
                    }
                ),
            ]
        ),
        encoding="utf-8",
    )
    ledger = IngestionLedger(ledger_path)
    state = ledger.get("doc-1")
    assert state is not None
    assert state.state is LedgerState.COMPLETED


def test_delta_application(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = IngestionLedger(ledger_path, auto_snapshot_interval=timedelta(days=7))
    ledger.update_state("doc-1", LedgerState.FETCHING)
    ledger.update_state("doc-1", LedgerState.FETCHED)
    snapshot = ledger.create_snapshot()
    ledger.update_state("doc-1", LedgerState.PARSING)
    loaded = ledger.load_with_compaction(snapshot, ledger_path)
    assert loaded["doc-1"].state is LedgerState.PARSING


def test_terminal_retryable_helpers() -> None:
    assert is_terminal_state(LedgerState.COMPLETED) is True
    assert is_retryable_state(LedgerState.FAILED) is True
    assert is_retryable_state(LedgerState.PENDING) is False
