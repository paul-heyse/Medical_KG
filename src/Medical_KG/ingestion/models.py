from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Mapping

from Medical_KG.ingestion.types import DocumentRaw, JSONMapping, MutableJSONMapping


@dataclass(slots=True)
class Document:
    """Canonical ingestion document representation."""

    doc_id: str
    source: str
    content: str
    metadata: MutableJSONMapping = field(default_factory=dict)
    raw: DocumentRaw | None = None

    def as_record(self) -> Mapping[str, object]:
        record: dict[str, object] = {
            "doc_id": self.doc_id,
            "source": self.source,
            "content": self.content,
            "metadata": dict(self.metadata),
        }
        if self.raw is not None:
            record["raw"] = self.raw
        else:
            record["raw"] = None
        return record


@dataclass(slots=True)
class IngestionResult:
    document: Document
    state: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: JSONMapping = field(default_factory=dict)
