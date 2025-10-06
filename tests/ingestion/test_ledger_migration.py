from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from Medical_KG.ingestion.ledger import IngestionLedger, LedgerState


def _load_migration_module():
    module_path = Path(__file__).resolve().parents[2] / "scripts" / "archive" / "migrate_ledger_to_state_machine.py"
    spec = importlib.util.spec_from_file_location(
        "ledger_migration", module_path
    )
    if spec is None or spec.loader is None:  # pragma: no cover - defensive guard
        raise RuntimeError("Unable to load migration module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def test_migrate_ledger_to_state_machine(tmp_path: Path) -> None:
    legacy_path = tmp_path / "legacy-ledger.jsonl"
    sequence = [
        "pending",
        "fetching",
        "fetched",
        "parsing",
        "parsed",
        "validating",
        "validated",
        "ir_building",
        "pdf_ir_ready",
        "completed",
    ]
    rows = [
        {
            "doc_id": "doc-1",
            "state": state,
            "timestamp": 1700000000 + offset,
            "metadata": {"source": "stub"} if offset == 0 else {},
        }
        for offset, state in enumerate(sequence)
    ]
    legacy_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    migration = _load_migration_module()
    output_path = tmp_path / "migrated-ledger.jsonl"
    result = migration.migrate_ledger(
        legacy_path,
        output_path=output_path,
        dry_run=False,
        create_backup=True,
        progress_interval=2,
    )
    assert result == output_path
    assert output_path.exists()
    backup_path = legacy_path.with_suffix(legacy_path.suffix + ".bak")
    assert backup_path.exists(), "expected legacy ledger backup"

    ledger = IngestionLedger(output_path)
    state = ledger.get("doc-1")
    assert state is not None
    assert state.state is LedgerState.COMPLETED
    history_states = [audit.new_state for audit in ledger.get_state_history("doc-1")]
    assert LedgerState.FETCHING in history_states
    assert LedgerState.IR_READY in history_states


def test_migrate_ledger_dry_run_reports(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    legacy_path = tmp_path / "legacy.jsonl"
    legacy_path.write_text(
        json.dumps({"doc_id": "doc-2", "state": "completed", "timestamp": 1700000100}),
        encoding="utf-8",
    )
    migration = _load_migration_module()
    result = migration.migrate_ledger(legacy_path, dry_run=True, create_backup=False)
    assert result is None
    captured = capsys.readouterr()
    assert "Ledger contains" in captured.err
