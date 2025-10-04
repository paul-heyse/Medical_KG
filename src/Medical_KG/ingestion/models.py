from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping

from Medical_KG.ingestion.ledger import LedgerState
from Medical_KG.ingestion.types import DocumentRaw, JSONMapping, MutableJSONMapping


@dataclass(slots=True)
class Document:
    """Canonical ingestion document representation."""

    doc_id: str
    source: str
    content: str
    metadata: MutableJSONMapping = field(default_factory=dict)
    raw: DocumentRaw

    def __post_init__(self) -> None:
        if self.raw is None:
            raise ValueError(
                "Document.raw is required; ensure adapters emit typed payloads before constructing Document instances."
            )
        if not isinstance(self.raw, Mapping):
            raise TypeError(
                "Document.raw must be a mapping produced by a typed adapter payload."
            )

    def as_record(self) -> Mapping[str, object]:
        record: dict[str, object] = {
            "doc_id": self.doc_id,
            "source": self.source,
            "content": self.content,
            "metadata": dict(self.metadata),
        }
        record["raw"] = self.raw
        return record


@dataclass(slots=True)
class IngestionResult:
    document: Document
    state: LedgerState
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: JSONMapping = field(default_factory=dict)
