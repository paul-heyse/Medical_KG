from __future__ import annotations

import csv
import gzip
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from Medical_KG.security import AuditEvent, AuditLogger

from .fixtures import sample_audit_payload


def test_log_creation_and_query(tmp_path: Path) -> None:
    logger = AuditLogger(tmp_path / "audit.log")
    timestamp = datetime.now(timezone.utc)
    logger.log(AuditEvent(category="login", payload=sample_audit_payload(0), actor="alice", resource="console", timestamp=timestamp))
    logger.log(AuditEvent(category="access", payload=sample_audit_payload(1), actor="bob", resource="console"))

    records = logger.read()
    assert len(records) == 2
    assert records[0]["category"] == "login"
    assert logger.verify_integrity()

    results = logger.query(actor="alice")
    assert len(results) == 1
    assert results[0]["payload"]["resource"] == "doc-0"

    future = timestamp + timedelta(minutes=1)
    assert logger.query(since=future) == []


def test_log_export_and_rotation(tmp_path: Path) -> None:
    logger = AuditLogger(tmp_path / "audit.log")
    for index in range(5):
        logger.log(AuditEvent(category="access", payload=sample_audit_payload(index)))
    export_path = tmp_path / "audit.json.gz"
    logger.export(export_path, format="json", page_size=2)
    with gzip.open(export_path, "rt", encoding="utf-8") as handle:
        lines = handle.readlines()
    assert len(lines) == 3  # 5 entries chunked into 3 batches

    csv_path = tmp_path / "audit.csv"
    logger.export(csv_path, format="csv")
    with csv_path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    assert len(rows) == 5
    assert rows[0]["category"] == "access"

    archive = logger.rotate(max_entries=2)
    assert archive is not None and archive.exists()
    assert not (tmp_path / "audit.log").exists()


def test_log_integrity_failure(tmp_path: Path) -> None:
    logger = AuditLogger(tmp_path / "audit.log")
    logger.log(AuditEvent(category="access", payload={"action": "read"}))
    path = tmp_path / "audit.log"
    contents = path.read_text(encoding="utf-8")
    path.write_text(contents.replace("read", "write"), encoding="utf-8")
    assert logger.verify_integrity() is False


def test_export_invalid_format(tmp_path: Path) -> None:
    logger = AuditLogger(tmp_path / "audit.log")
    logger.log(AuditEvent(category="access", payload={}))
    with pytest.raises(ValueError):
        logger.export(tmp_path / "audit.bin", format="binary")
