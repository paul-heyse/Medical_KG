from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping

from Medical_KG.ingestion.types import DocumentRaw, JSONMapping, JSONValue, MutableJSONMapping


@dataclass(slots=True)
class Document:
    """Canonical ingestion document representation."""

    doc_id: str
    source: str
    content: str
    metadata: MutableJSONMapping = field(default_factory=dict)
    raw: DocumentRaw | None = None

    def as_record(self) -> Mapping[str, JSONValue]:
        return {
            "doc_id": self.doc_id,
            "source": self.source,
            "content": self.content,
            "metadata": dict(self.metadata),
            "raw": self.raw,
        }


@dataclass(slots=True)
class IngestionResult:
    document: Document
    state: str
    timestamp: datetime
    metadata: JSONMapping = field(default_factory=dict)
