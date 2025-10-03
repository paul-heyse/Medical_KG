from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Iterable, Mapping, Protocol, cast

import jsonlines

from Medical_KG.ingestion.types import JSONMapping, JSONValue


class _JsonLinesWriter(Protocol):
    def write(self, obj: object) -> None: ...


@dataclass(slots=True)
class LedgerEntry:
    doc_id: str
    state: str
    timestamp: datetime
    metadata: JSONMapping


class IngestionLedger:
    """Durable JSONL-backed ledger tracking ingestion state transitions."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._lock = Lock()
        self._latest: dict[str, LedgerEntry] = {}
        if path.exists():
            with jsonlines.open(path, mode="r") as fp:
                for row in cast(Iterable[Mapping[str, object]], fp):
                    doc_id = str(row["doc_id"])
                    state = str(row["state"])
                    timestamp_raw = row["timestamp"]
                    timestamp = datetime.fromisoformat(str(timestamp_raw))
                    metadata_raw = row.get("metadata", {})
                    metadata: dict[str, JSONValue]
                    if isinstance(metadata_raw, Mapping):
                        metadata = {
                            str(key): cast(JSONValue, value)
                            for key, value in metadata_raw.items()
                        }
                    else:
                        metadata = {}
                    entry = LedgerEntry(
                        doc_id=doc_id,
                        state=state,
                        timestamp=timestamp,
                        metadata=metadata,
                    )
                    self._latest[entry.doc_id] = entry

    def record(self, doc_id: str, state: str, metadata: Mapping[str, JSONValue] | None = None) -> LedgerEntry:
        entry_metadata: dict[str, JSONValue] = dict(metadata) if metadata is not None else {}
        entry = LedgerEntry(
            doc_id=doc_id,
            state=state,
            timestamp=datetime.now(timezone.utc),
            metadata=entry_metadata,
        )
        payload = {
            "doc_id": entry.doc_id,
            "state": entry.state,
            "timestamp": entry.timestamp.isoformat(),
            "metadata": entry.metadata,
        }
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with jsonlines.open(self._path, mode="a") as fp:
                cast(_JsonLinesWriter, fp).write(payload)
            self._latest[doc_id] = entry
        return entry

    def get(self, doc_id: str) -> LedgerEntry | None:
        return self._latest.get(doc_id)

    def entries(self, *, state: str | None = None) -> Iterable[LedgerEntry]:
        entries = list(self._latest.values())
        if state is None:
            return entries
        return [entry for entry in entries if entry.state == state]
