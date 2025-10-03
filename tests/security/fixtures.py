from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable

LICENSE_YAML = """
    vocabs:
      SNOMED:
        licensed: true
        territory: global
      MEDDRA:
        licensed: false
      LOINC:
        licensed: true
    tiers:
      free:
        vocabs:
          MEDDRA: false
          SNOMED: false
        features:
          briefing: false
          kg-write: false
        usage_limits:
          requests_per_day: 10
        redactions:
          SNOMED: "[upgrade-required]"
        grace_period_days: 1
      basic:
        vocabs:
          SNOMED: true
          MEDDRA: false
        features:
          briefing: true
          kg-write: false
        usage_limits:
          requests_per_day: 100
        redactions:
          MEDDRA: "[upgrade-required]"
        grace_period_days: 3
      pro:
        vocabs:
          SNOMED: true
          MEDDRA: true
        features:
          briefing: true
          kg-write: true
        usage_limits:
          requests_per_day: 1000
        redactions: {}
        grace_period_days: 7
      enterprise:
        vocabs:
          SNOMED: true
          MEDDRA: true
          LOINC: true
        features:
          briefing: true
          kg-write: true
        usage_limits:
          requests_per_day: 100000
        redactions: {}
        grace_period_days: 30
"""


def write_license_file(tmp_path: Path) -> Path:
    path = tmp_path / "licenses.yml"
    path.write_text(LICENSE_YAML, encoding="utf-8")
    return path


@dataclass(slots=True)
class MockUser:
    user_id: str
    roles: tuple[str, ...]


def sample_users() -> Iterable[MockUser]:
    return (
        MockUser("alice", ("analyst",)),
        MockUser("bob", ("analyst", "admin")),
        MockUser("eve", ("viewer",)),
    )


def sample_audit_payload(index: int) -> dict[str, object]:
    return {"index": index, "action": "read", "resource": f"doc-{index}"}


def sample_retention_records(now: datetime) -> list[tuple[str, datetime, dict[str, object], tuple[str, ...]]]:
    return [
        (
            "recent",
            now - timedelta(days=1),
            {"pii": "Alice", "notes": "recent"},
            ("public",),
        ),
        (
            "old",
            now - timedelta(days=120),
            {"pii": "Bob", "notes": "expired"},
            (),
        ),
        (
            "exempt",
            now - timedelta(days=400),
            {"pii": "Charlie", "notes": "exempt"},
            ("legal-hold",),
        ),
    ]


def days_ago(days: int) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=days)
