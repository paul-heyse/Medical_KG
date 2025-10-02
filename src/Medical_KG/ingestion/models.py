from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping, MutableMapping


@dataclass(slots=True)
class Document:
    """Canonical ingestion document representation."""

    doc_id: str
    source: str
    content: str
    metadata: MutableMapping[str, Any] = field(default_factory=dict)
    raw: Any | None = None

    def as_record(self) -> Mapping[str, Any]:
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
    metadata: Mapping[str, Any] = field(default_factory=dict)
