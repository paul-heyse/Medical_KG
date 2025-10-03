"""Structured audit logging."""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Iterator, Mapping, Sequence


@dataclass(slots=True)
class AuditEvent:
    category: str
    payload: Mapping[str, object]
    actor: str | None = None
    resource: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class AuditLogger:
    """Writes audit events to append-only JSONL file with integrity checks."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: AuditEvent) -> None:
        record = {
            "category": event.category,
            "timestamp": event.timestamp.isoformat(),
            "payload": dict(event.payload),
            "actor": event.actor,
            "resource": event.resource,
        }
        previous_hash = self._tail_hash()
        record["previous_hash"] = previous_hash
        serialized = json.dumps(record, sort_keys=True)
        record_hash = hashlib.sha256((previous_hash + serialized).encode("utf-8")).hexdigest()
        record["hash"] = record_hash
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def read(self) -> Sequence[Mapping[str, object]]:
        return list(self._iter_records())

    def query(
        self,
        *,
        category: str | None = None,
        actor: str | None = None,
        resource: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> Sequence[Mapping[str, object]]:
        results = []
        for record in self._iter_records():
            timestamp = datetime.fromisoformat(str(record["timestamp"]))
            if category and record.get("category") != category:
                continue
            if actor and record.get("actor") != actor:
                continue
            if resource and record.get("resource") != resource:
                continue
            if since and timestamp < since:
                continue
            if until and timestamp > until:
                continue
            results.append(record)
        return results

    def export(self, destination: Path, *, format: str = "json", page_size: int = 500) -> Path:
        records = self._iter_records()
        if format == "json":
            with gzip.open(destination, "wt", encoding="utf-8") as handle:
                for chunk in _chunked(records, page_size):
                    handle.write(json.dumps(chunk) + "\n")
        elif format == "csv":
            with destination.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["timestamp", "category", "actor", "resource", "payload", "hash"])
                writer.writeheader()
                for record in records:
                    writer.writerow(
                        {
                            "timestamp": record["timestamp"],
                            "category": record["category"],
                            "actor": record.get("actor"),
                            "resource": record.get("resource"),
                            "payload": json.dumps(record["payload"], sort_keys=True),
                            "hash": record["hash"],
                        }
                    )
        else:
            raise ValueError(f"Unsupported export format {format}")
        return destination

    def rotate(self, *, max_entries: int = 1000) -> Path | None:
        records = self.read()
        if len(records) <= max_entries:
            return None
        archive_path = self._path.with_suffix(".gz")
        with gzip.open(archive_path, "wt", encoding="utf-8") as handle:
            for record in records:
                handle.write(json.dumps(record) + "\n")
        self._path.unlink()
        return archive_path

    def verify_integrity(self) -> bool:
        previous = ""
        for record in self._iter_records():
            record_hash = str(record.get("hash", ""))
            previous_hash = str(record.get("previous_hash", ""))
            payload = {k: v for k, v in record.items() if k != "hash"}
            serialized = json.dumps(payload, sort_keys=True)
            expected = hashlib.sha256((previous_hash + serialized).encode("utf-8")).hexdigest()
            if expected != record_hash or (previous and previous_hash != previous):
                return False
            previous = record_hash
        return True

    def _iter_records(self) -> Iterator[Mapping[str, object]]:
        if not self._path.exists():
            return iter(())

        def iterator() -> Iterator[Mapping[str, object]]:
            with self._path.open("r", encoding="utf-8") as handle:
                for line in handle:
                    yield json.loads(line)

        return iterator()

    def _tail_hash(self) -> str:
        if not self._path.exists():
            return ""
        with self._path.open("rb") as handle:
            handle.seek(0, 2)
            position = handle.tell()
            if position == 0:
                return ""
            chunk = b""
            while position > 0 and b"\n" not in chunk:
                step = min(1024, position)
                position -= step
                handle.seek(position)
                chunk = handle.read(step) + chunk
            lines = chunk.splitlines()
            if not lines:  # pragma: no cover - unreachable due to earlier size check
                return ""
            for raw_line in reversed(lines):
                text = raw_line.decode("utf-8").strip()
                if not text:
                    continue
                positions = [idx for idx, char in enumerate(text) if char == "{"]
                for pos in positions:
                    try:
                        last = json.loads(text[pos:])
                    except json.JSONDecodeError:  # pragma: no cover - defensive guard
                        continue
                    return str(last.get("hash", ""))
            return ""


def _chunked(iterator: Iterator[Mapping[str, object]], size: int) -> Iterable[list[Mapping[str, object]]]:
    chunk: list[Mapping[str, object]] = []
    for item in iterator:
        chunk.append(item)
        if len(chunk) == size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


__all__ = ["AuditLogger", "AuditEvent"]
