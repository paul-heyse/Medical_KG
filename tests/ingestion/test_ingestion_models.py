from __future__ import annotations

from datetime import datetime, timezone

import pytest

from Medical_KG.ingestion.ledger import LedgerState
from Medical_KG.ingestion.models import Document, IngestionResult
from Medical_KG.ingestion.types import PubMedDocumentPayload


def test_document_as_record_round_trip() -> None:
    document = Document(
        doc_id="doc-1",
        source="demo",
        content="body",
        metadata={"key": "value"},
        raw=_minimal_raw("doc-1", "body"),
    )
    record = document.as_record()
    assert record["doc_id"] == "doc-1"
    assert record["metadata"]["key"] == "value"


def test_ingestion_result_container() -> None:
    document = Document(
        "doc-2",
        "demo",
        "content",
        raw=_minimal_raw("doc-2", "content"),
    )
    result = IngestionResult(
        document=document, state=LedgerState.COMPLETED, timestamp=datetime.now(timezone.utc)
    )
    assert result.document.doc_id == "doc-2"
    assert result.state is LedgerState.COMPLETED


def test_document_requires_raw_payload() -> None:
    with pytest.raises(ValueError):
        Document(
            doc_id="doc-3",
            source="demo",
            content="body",
            metadata={},
            raw=None,  # type: ignore[arg-type]
        )


def _minimal_raw(doc_id: str, content: str) -> PubMedDocumentPayload:
    return {
        "pmid": doc_id,
        "title": content or "Untitled",
        "abstract": content,
        "authors": [],
        "mesh_terms": [],
        "pub_types": [],
    }
