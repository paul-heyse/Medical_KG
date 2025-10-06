from __future__ import annotations

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import perf_counter

import pytest

from Medical_KG.ingestion.ledger import (
    IngestionLedger,
    InvalidStateTransition,
    LedgerAuditRecord,
    LedgerCorruption,
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
    with pytest.raises(InvalidStateTransition) as excinfo:
        validate_transition(LedgerState.FETCHING, LedgerState.IR_READY)
    assert "FETCHING" in str(excinfo.value)
    assert "IR_READY" in str(excinfo.value)


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
    with pytest.warns(DeprecationWarning):
        ledger.record("doc-1", "completed")  # type: ignore[arg-type]


def test_alias_entries_still_parse(tmp_path: Path) -> None:
    ledger_path = tmp_path / "aliases.jsonl"
    timestamp = datetime.now(timezone.utc).timestamp()
    ledger_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "doc_id": "doc-1",
                        "old_state": "IR_BUILDING",
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


def test_unknown_state_marker_raises(tmp_path: Path) -> None:
    ledger_path = tmp_path / "invalid-state.jsonl"
    timestamp = datetime.now(timezone.utc).timestamp()
    ledger_path.write_text(
        json.dumps(
            {
                "doc_id": "doc-1",
                "old_state": "FETCHING",
                "new_state": "deprecated_state",
                "timestamp": timestamp,
                "adapter": "stub",
                "metadata": {},
                "parameters": {},
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(LedgerCorruption) as excinfo:
        IngestionLedger(ledger_path)
    assert "unknown ledger state" in str(excinfo.value)


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


def test_compaction_initialization_is_faster(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ledger_path = tmp_path / "compaction.jsonl"
    ledger = IngestionLedger(ledger_path, auto_snapshot_interval=timedelta(days=30))
    ledger._refresh_state_metrics = lambda: None  # type: ignore[assignment]
    for index in range(200):
        doc_id = f"doc-{index}"
        ledger.update_state(doc_id, LedgerState.PENDING)
        ledger.update_state(doc_id, LedgerState.FETCHING)
        ledger.update_state(doc_id, LedgerState.FETCHED)
        ledger.update_state(doc_id, LedgerState.PARSING)
        ledger.update_state(doc_id, LedgerState.PARSED)
        ledger.update_state(doc_id, LedgerState.VALIDATING)
        ledger.update_state(doc_id, LedgerState.VALIDATED)
        ledger.update_state(doc_id, LedgerState.IR_BUILDING)
        ledger.update_state(doc_id, LedgerState.IR_READY)
        ledger.update_state(doc_id, LedgerState.COMPLETED)

    import Medical_KG.ingestion.ledger as ledger_module

    original_open = ledger_module.jsonlines.open
    delay = 0.0005

    class _SlowReader:
        def __init__(self, handle: object) -> None:
            self._handle = handle

        def __iter__(self):
            for row in self._handle:  # type: ignore[attr-defined]
                time.sleep(delay)
                yield row

        def __getattr__(self, name: str) -> object:
            return getattr(self._handle, name)

        def __enter__(self) -> "_SlowReader":
            self._handle.__enter__()
            return self

        def __exit__(self, *exc: object) -> object:
            return self._handle.__exit__(*exc)

    def _slow_open(path: Path | str, *args: object, **kwargs: object):
        reader = original_open(path, *args, **kwargs)
        mode = kwargs.get("mode")
        if mode is None and len(args) >= 1:
            mode = args[0]
        if not isinstance(mode, str):
            mode = "r"
        if "r" in mode and Path(path) == ledger_path:
            return _SlowReader(reader)
        return reader

    monkeypatch.setattr(ledger_module.jsonlines, "open", _slow_open)

    def _load_once() -> float:
        start = perf_counter()
        instance = IngestionLedger(ledger_path)
        instance._refresh_state_metrics = lambda: None  # type: ignore[assignment]
        instance.entries()
        duration = perf_counter() - start
        return duration

    baseline = _load_once()
    compaction_ledger = IngestionLedger(ledger_path)
    compaction_ledger._refresh_state_metrics = lambda: None  # type: ignore[assignment]
    compaction_ledger.create_snapshot()
    del compaction_ledger
    optimized = _load_once()
    assert optimized < baseline
    assert baseline - optimized > 0.05


def test_record_accepts_string_state_with_warning(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "string-ledger.jsonl")
    with pytest.warns(DeprecationWarning):
        audit = ledger.record("doc-1", "completed", adapter="stub")
    assert audit.new_state is LedgerState.COMPLETED
    entry = ledger.get("doc-1")
    assert entry is not None
    assert entry.state is LedgerState.COMPLETED


def test_concurrent_state_updates(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "concurrent-ledger.jsonl")
    ledger._refresh_state_metrics = lambda: None  # type: ignore[assignment]

    sequences = [
        (
            LedgerState.PENDING,
            LedgerState.FETCHING,
            LedgerState.FETCHED,
            LedgerState.PARSING,
            LedgerState.PARSED,
            LedgerState.VALIDATING,
            LedgerState.VALIDATED,
            LedgerState.IR_BUILDING,
            LedgerState.IR_READY,
            LedgerState.COMPLETED,
        ),
        (
            LedgerState.PENDING,
            LedgerState.FETCHING,
            LedgerState.FAILED,
            LedgerState.RETRYING,
            LedgerState.FETCHING,
            LedgerState.FETCHED,
            LedgerState.PARSING,
            LedgerState.PARSED,
            LedgerState.VALIDATING,
            LedgerState.VALIDATED,
            LedgerState.IR_BUILDING,
            LedgerState.IR_READY,
            LedgerState.COMPLETED,
        ),
    ]

    def _worker(doc_id: str, states: tuple[LedgerState, ...]) -> None:
        for state in states:
            ledger.update_state(doc_id, state, adapter="test")

    doc_ids = [f"doc-{idx}" for idx in range(8)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [
            executor.submit(_worker, doc_id, sequences[idx % len(sequences)])
            for idx, doc_id in enumerate(doc_ids)
        ]
        for future in futures:
            future.result()

    for idx, doc_id in enumerate(doc_ids):
        entry = ledger.get(doc_id)
        assert entry is not None
        expected = sequences[idx % len(sequences)][-1]
        assert entry.state is expected


@pytest.mark.skipif(
    os.getenv("LEDGER_STRESS_TEST") != "1",
    reason="Set LEDGER_STRESS_TEST=1 to enable 1M entry performance regression",
)
def test_compaction_handles_one_million_entries(tmp_path: Path) -> None:
    ledger_path = tmp_path / "stress-ledger.jsonl"
    documents = 1_000_000
    states = [
        "PENDING",
        "FETCHING",
        "FETCHED",
        "PARSING",
        "PARSED",
        "VALIDATING",
        "VALIDATED",
        "IR_BUILDING",
        "IR_READY",
        "COMPLETED",
    ]
    with ledger_path.open("w", encoding="utf-8") as handle:
        for index in range(documents):
            doc_id = f"doc-{index}"
            previous = states[0]
            timestamp = datetime.now(timezone.utc).timestamp()
            for state in states[1:]:
                payload = {
                    "doc_id": doc_id,
                    "old_state": previous,
                    "new_state": state,
                    "timestamp": timestamp,
                    "adapter": "stress",
                    "metadata": {},
                    "parameters": {},
                }
                handle.write(json.dumps(payload) + "\n")
                previous = state
                timestamp += 1

    ledger = IngestionLedger(ledger_path)
    ledger._refresh_state_metrics = lambda: None  # type: ignore[assignment]
    assert len(ledger.entries()) == documents
