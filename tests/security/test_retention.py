from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from Medical_KG.security import (
    AuditLogger,
    PurgePipeline,
    RetentionPolicy,
    RetentionRecord,
)

from .fixtures import sample_retention_records


def _pipeline() -> PurgePipeline:
    raw: dict[str, bytes] = {}
    ir: dict[str, dict[str, object]] = {}
    chunk: dict[str, dict[str, object]] = {}
    embedding: dict[str, dict[str, object]] = {}
    kg: dict[str, dict[str, object]] = {}
    return PurgePipeline(raw, ir, chunk, embedding, kg)


def test_policy_execution_and_audit(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    pipeline = _pipeline()
    logger = AuditLogger(tmp_path / "audit.log")
    records = [
        RetentionRecord(doc_id=doc_id, created_at=created_at, data=data, tags=tags)
        for doc_id, created_at, data, tags in sample_retention_records(now)
    ]
    for record in records:
        pipeline.raw_store[record.doc_id] = b"raw"
        pipeline.ir_store[record.doc_id] = {"doc": record.doc_id}
    policy = RetentionPolicy(
        name="default",
        retention_days=90,
        anonymize_fields=("pii",),
        exempt_tags=frozenset({"legal-hold"}),
    )
    result = policy.execute(records, pipeline, now=now, audit_logger=logger)

    assert "old" in result.deleted
    assert pipeline.exists_anywhere("old") is False
    assert pipeline.exists_anywhere("recent") is True
    assert "exempt" in result.skipped
    assert records[1].data["pii"] == "[anonymized]"
    assert logger.verify_integrity()


def test_policy_dry_run(tmp_path: Path) -> None:
    now = datetime.now(timezone.utc)
    pipeline = _pipeline()
    records = [RetentionRecord(doc_id="old", created_at=now - timedelta(days=200), data={}, tags=())]
    policy = RetentionPolicy(name="dry", retention_days=30, dry_run=True)
    result = policy.execute(records, pipeline, now=now)
    assert result.deleted == ()
    assert result.dry_run_report == ("old",)


def test_policy_schedule() -> None:
    policy = RetentionPolicy(name="sched", retention_days=90, interval_minutes=60)
    start = datetime(2024, 1, 1, tzinfo=timezone.utc)
    assert policy.next_run(after=start) == datetime(2024, 1, 1, 1, tzinfo=timezone.utc)
