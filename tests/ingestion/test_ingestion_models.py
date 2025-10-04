from __future__ import annotations

from datetime import datetime, timezone

from Medical_KG.ingestion.ledger import LedgerState
from Medical_KG.ingestion.models import Document, IngestionResult


def test_document_as_record_round_trip() -> None:
    document = Document(
        doc_id="doc-1",
        source="demo",
        content="body",
        metadata={"key": "value"},
        raw={"field": 1},
    )
    record = document.as_record()
    assert record["doc_id"] == "doc-1"
    assert record["metadata"]["key"] == "value"


def test_ingestion_result_container() -> None:
    document = Document("doc-2", "demo", "content")
    result = IngestionResult(
        document=document, state=LedgerState.COMPLETED, timestamp=datetime.now(timezone.utc)
    )
    assert result.document.doc_id == "doc-2"
    assert result.state is LedgerState.COMPLETED
