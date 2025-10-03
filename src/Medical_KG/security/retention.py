"""Data retention and purge pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, MutableMapping

from .audit import AuditEvent, AuditLogger


@dataclass(slots=True)
class PurgePipeline:
    """Deletes documents across storage layers in correct order."""

    raw_store: MutableMapping[str, bytes]
    ir_store: MutableMapping[str, dict[str, object]]
    chunk_store: MutableMapping[str, dict[str, object]]
    embedding_store: MutableMapping[str, dict[str, object]]
    kg_store: MutableMapping[str, dict[str, object]]

    def purge(self, doc_id: str) -> None:
        self.raw_store.pop(doc_id, None)
        self.ir_store.pop(doc_id, None)
        self.chunk_store.pop(doc_id, None)
        self.embedding_store.pop(doc_id, None)
        self.kg_store.pop(doc_id, None)

    def exists_anywhere(self, doc_id: str) -> bool:
        return any(
            doc_id in store
            for store in (
                self.raw_store,
                self.ir_store,
                self.chunk_store,
                self.embedding_store,
                self.kg_store,
            )
        )


__all__ = ["PurgePipeline"]


@dataclass(slots=True)
class RetentionRecord:
    doc_id: str
    created_at: datetime
    data: MutableMapping[str, object]
    tags: tuple[str, ...] = ()


@dataclass(slots=True)
class RetentionResult:
    deleted: tuple[str, ...]
    anonymized: tuple[str, ...]
    skipped: tuple[str, ...]
    dry_run_report: tuple[str, ...]


@dataclass(slots=True)
class RetentionPolicy:
    name: str
    retention_days: int
    anonymize_fields: tuple[str, ...] = ()
    dry_run: bool = False
    exempt_tags: frozenset[str] = frozenset()
    interval_minutes: int = 24 * 60

    def execute(
        self,
        records: Iterable[RetentionRecord],
        pipeline: PurgePipeline,
        *,
        now: datetime | None = None,
        audit_logger: AuditLogger | None = None,
    ) -> RetentionResult:
        current = now or datetime.now(timezone.utc)
        threshold = current - timedelta(days=self.retention_days)
        deleted: list[str] = []
        anonymized: list[str] = []
        skipped: list[str] = []
        dry_run_report: list[str] = []
        for record in records:
            if self.exempt_tags & set(record.tags):
                skipped.append(record.doc_id)
                continue
            if record.created_at >= threshold:
                skipped.append(record.doc_id)
                continue
            if self.dry_run:
                dry_run_report.append(record.doc_id)
                continue
            for field in self.anonymize_fields:
                if field in record.data and record.data[field] is not None:
                    record.data[field] = "[anonymized]"
                    anonymized.append(record.doc_id)
            pipeline.purge(record.doc_id)
            deleted.append(record.doc_id)
            if audit_logger:
                audit_logger.log(
                    AuditEvent(
                        category="retention",
                        payload={"document": record.doc_id, "policy": self.name},
                    )
                )
        return RetentionResult(
            deleted=tuple(deleted),
            anonymized=tuple(sorted(set(anonymized))),
            skipped=tuple(sorted(set(skipped))),
            dry_run_report=tuple(dry_run_report),
        )

    def next_run(self, *, after: datetime | None = None) -> datetime:
        base = after or datetime.now(timezone.utc)
        return base + timedelta(minutes=self.interval_minutes)


__all__.extend(["RetentionPolicy", "RetentionRecord", "RetentionResult"])
