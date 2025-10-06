from __future__ import annotations

from pathlib import Path

from Medical_KG.ingestion.ledger import IngestionLedger, LedgerState


def test_ledger_persists_entries(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = IngestionLedger(ledger_path)
    ledger.update_state("doc1", LedgerState.COMPLETED, metadata={"source": "pubmed"})
    ledger.update_state("doc2", LedgerState.FETCHED, metadata={"source": "pmc"})

    reloaded = IngestionLedger(ledger_path)
    doc1 = reloaded.get("doc1")
    doc2 = reloaded.get("doc2")
    assert doc1 is not None and doc1.state is LedgerState.COMPLETED
    assert doc2 is not None and doc2.state is LedgerState.FETCHED


def test_ledger_entries_returns_latest(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    ledger.update_state("doc1", LedgerState.FETCHING)
    ledger.update_state("doc1", LedgerState.FETCHED)
    ledger.update_state("doc1", LedgerState.PARSING)
    ledger.update_state("doc1", LedgerState.PARSED)
    ledger.update_state("doc1", LedgerState.VALIDATING)
    ledger.update_state("doc1", LedgerState.VALIDATED)
    ledger.update_state("doc1", LedgerState.IR_BUILDING)
    ledger.update_state("doc1", LedgerState.IR_READY)
    ledger.update_state("doc1", LedgerState.COMPLETED)
    entries = {entry.doc_id: entry.state for entry in ledger.entries()}
    assert entries == {"doc1": LedgerState.COMPLETED}
    pdf_entries = list(ledger.entries(state=LedgerState.FETCHED))
    assert pdf_entries == []
