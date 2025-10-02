"""Structured audit logging."""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(slots=True)
class AuditEvent:
    category: str
    payload: Mapping[str, object]
    timestamp: datetime = datetime.now(timezone.utc)


class AuditLogger:
    """Writes audit events to append-only JSONL file."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def log(self, event: AuditEvent) -> None:
        record = {
            "category": event.category,
            "timestamp": event.timestamp.isoformat(),
            "payload": dict(event.payload),
        }
        with self._path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record) + "\n")

    def read(self) -> Iterable[Mapping[str, object]]:
        if not self._path.exists():
            return []
        with self._path.open("r", encoding="utf-8") as handle:
            return [json.loads(line) for line in handle]


__all__ = ["AuditLogger", "AuditEvent"]
