from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from Medical_KG.security import (
    AuditLogger,
    ExtractionActivity,
    LicenseRegistry,
    ProvenanceStore,
    PurgePipeline,
    ScopeEnforcer,
    validate_shacl,
)
from Medical_KG.security.audit import AuditEvent


def test_license_registry_filters_labels(tmp_path: Path) -> None:
    path = tmp_path / "licenses.yml"
    path.write_text(
        """
        vocabs:
          SNOMED:
            licensed: true
          MEDDRA:
            licensed: false
        tiers:
          internal:
            SNOMED: true
            MEDDRA: false
        """,
        encoding="utf-8",
    )
    registry = LicenseRegistry.from_yaml(path)
    assert registry.filter_labels("SNOMED", "internal", "Heart failure") == "Heart failure"
    assert "license" in registry.filter_labels("MEDDRA", "internal", "Nausea")


def test_scope_enforcer() -> None:
    enforcer = ScopeEnforcer(["admin", "retrieve:read"])
    enforcer.verify(["admin", "retrieve:read", "ingest:write"])
    with pytest.raises(PermissionError):
        enforcer.verify(["admin"])


def test_provenance_and_audit(tmp_path: Path) -> None:
    store = ProvenanceStore()
    activity = ExtractionActivity(
        activity_id="act-1",
        model="model-x",
        version="1.0",
        prompt_hash="abc",
        schema_hash="def",
        timestamp=datetime.now(timezone.utc),
    )
    store.register_activity(activity)
    store.link_assertion("assert-1", "act-1")
    assert store.activity_for("assert-1").model == "model-x"

    logger = AuditLogger(tmp_path / "audit.log")
    logger.log(AuditEvent(category="write", payload={"id": "assert-1"}))
    events = list(logger.read())
    assert events[0]["category"] == "write"


def test_purge_pipeline_and_shacl() -> None:
    pipeline = PurgePipeline({}, {"doc": {}}, {"doc": {}}, {}, {"doc": {}})
    pipeline.purge("doc")
    assert not pipeline.exists_anywhere("doc")

    graph = {
        "evidence": [
            {"id": "e1", "unit_ucum": "mg", "spans": [{"start": 0, "end": 10}]},
            {"id": "e2", "unit_ucum": "", "spans": [{"start": 5, "end": 2}]},
        ],
        "adverse_events": [{"id": "ae1", "grade": 7}],
        "constraints": [{"id": "c1", "generated_by": ""}],
    }
    errors = validate_shacl(graph)
    assert len(errors) == 4

