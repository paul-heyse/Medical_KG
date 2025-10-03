from __future__ import annotations

from pathlib import Path

from Medical_KG.ingestion.ledger import IngestionLedger


def test_ledger_persists_entries(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = IngestionLedger(ledger_path)
    ledger.record("doc1", "auto_done", {"source": "pubmed"})
    ledger.record("doc2", "pdf_downloaded", {"source": "pmc"})

    reloaded = IngestionLedger(ledger_path)
    doc1 = reloaded.get("doc1")
    doc2 = reloaded.get("doc2")
    assert doc1 is not None and doc1.state == "auto_done"
    assert doc2 is not None and doc2.state == "pdf_downloaded"


def test_ledger_entries_returns_latest(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    ledger.record("doc1", "auto_inflight")
    ledger.record("doc1", "auto_done")
    entries = {entry.doc_id: entry.state for entry in ledger.entries()}
    assert entries == {"doc1": "auto_done"}
    pdf_entries = list(ledger.entries(state="pdf_downloaded"))
    assert pdf_entries == []
