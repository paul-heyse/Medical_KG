from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Iterable, Mapping

import jsonlines


@dataclass(slots=True)
class LedgerEntry:
    doc_id: str
    state: str
    timestamp: datetime
    metadata: Mapping[str, Any]


class IngestionLedger:
    """Durable JSONL-backed ledger tracking ingestion state transitions."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()
        self._latest: Dict[str, LedgerEntry] = {}
        if path.exists():
            with jsonlines.open(path, mode="r") as reader:
                for row in reader:
                    entry = LedgerEntry(
                        doc_id=row["doc_id"],
                        state=row["state"],
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        metadata=row.get("metadata", {}),
                    )
                    self._latest[entry.doc_id] = entry

    def record(self, doc_id: str, state: str, metadata: Mapping[str, Any] | None = None) -> LedgerEntry:
        entry = LedgerEntry(
            doc_id=doc_id,
            state=state,
            timestamp=datetime.now(timezone.utc),
            metadata=metadata or {},
        )
        payload = {
            "doc_id": entry.doc_id,
            "state": entry.state,
            "timestamp": entry.timestamp.isoformat(),
            "metadata": entry.metadata,
        }
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with jsonlines.open(self._path, mode="a") as writer:
                writer.write(payload)
            self._latest[doc_id] = entry
        return entry

    def get(self, doc_id: str) -> LedgerEntry | None:
        return self._latest.get(doc_id)

    def entries(self, *, state: str | None = None) -> Iterable[LedgerEntry]:
        entries = self._latest.values()
        if state is None:
            return list(entries)
        return [entry for entry in entries if entry.state == state]
