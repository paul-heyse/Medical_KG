from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping, MutableMapping, Sequence


@dataclass(slots=True)
class Document:
    """Canonical ingestion document representation."""

    doc_id: str
    source: str
    content: str
    metadata: MutableMapping[str, object] = field(default_factory=dict)
    raw: Mapping[str, object] | Sequence[object] | str | bytes | None = None

    def as_record(self) -> Mapping[str, object]:
        record: dict[str, object] = {
            "doc_id": self.doc_id,
            "source": self.source,
            "content": self.content,
            "metadata": dict(self.metadata),
        }
        if self.raw is not None:
            record["raw"] = self.raw
        return record


@dataclass(slots=True)
class IngestionResult:
    document: Document
    state: str
    timestamp: datetime
    metadata: Mapping[str, object] = field(default_factory=dict)
