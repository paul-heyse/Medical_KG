from __future__ import annotations

from datetime import datetime, timezone

import pytest

from Medical_KG.security import ExtractionActivity, ProvenanceStore


def _activity(idx: int) -> ExtractionActivity:
    return ExtractionActivity(
        activity_id=f"act-{idx}",
        model="model-x",
        version="1.0",
        prompt_hash=f"prompt-{idx}",
        schema_hash=f"schema-{idx}",
        timestamp=datetime(2024, 1, idx + 1, tzinfo=timezone.utc),
    )


def test_lineage_tracking() -> None:
    store = ProvenanceStore()
    store.register_activity(_activity(1))
    store.register_activity(_activity(2))
    store.link_assertion("assert-1", "act-1")
    store.link_assertion("assert-2", "act-2")
    store.record_derivation("assert-2", "assert-1")

    assert store.activity_for("assert-1").model == "model-x"
    lineage = store.trace_lineage("assert-2")
    assert set(lineage) == {"assert-2", "assert-1"}


def test_prov_serialization() -> None:
    store = ProvenanceStore()
    store.register_activity(_activity(1))
    store.link_assertion("assert-1", "act-1")
    prov = store.prov_o()
    assert prov["entity"]["assert-1"]["prov:wasGeneratedBy"] == "act-1"
    assert prov["activity"]["act-1"]["prov:usedModel"] == "model-x"


def test_missing_activity_raises() -> None:
    store = ProvenanceStore()
    with pytest.raises(KeyError):
        store.link_assertion("assert-1", "act-unknown")


def test_graph_export() -> None:
    store = ProvenanceStore()
    store.register_activity(_activity(1))
    store.register_activity(_activity(2))
    store.link_assertion("assert-1", "act-1")
    store.link_assertion("assert-2", "act-2")
    store.record_derivation("assert-2", "assert-1")
    graph = store.as_graph()
    assert graph["assert-2"] == ("assert-1",)


def test_activity_for_missing_assertion() -> None:
    store = ProvenanceStore()
    store.register_activity(_activity(1))
    with pytest.raises(KeyError):
        store.activity_for("unknown")


def test_metadata_listing() -> None:
    store = ProvenanceStore()
    store.register_activity(_activity(1))
    store.link_assertion("assert-1", "act-1")
    meta = store.metadata()
    assert meta["assert-1"]["activity_id"] == "act-1"
