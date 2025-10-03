from __future__ import annotations

from typing import Any

import pytest

from Medical_KG.kg.writer import KnowledgeGraphWriter, WriteStatement
from tests.kg.fixtures import FakeNeo4jDriver


@pytest.fixture()
def writer() -> KnowledgeGraphWriter:
    return KnowledgeGraphWriter()


def test_merge_unknown_label_raises(writer: KnowledgeGraphWriter) -> None:
    with pytest.raises(ValueError, match="Unknown node label"):
        writer._merge_node("Unknown", {"id": "x"})  # type: ignore[attr-defined]


def test_write_document_and_chunk_relationship(writer: KnowledgeGraphWriter) -> None:
    writer.write_document({"uri": "doc://1", "id": "doc-1", "title": "Doc"})
    writer.write_chunk({"id": "chunk-1", "text": "hello"}, document_uri="doc://1", order=3)
    statements = list(writer.statements)
    assert any("MERGE (n:Document" in stmt.cypher for stmt in statements)
    rel = statements[-1]
    assert rel.cypher.endswith("MERGE (d)-[r:HAS_CHUNK]->(c) SET r.order = $order")
    assert rel.parameters["order"] == 3


def test_write_identifier_requires_fields(writer: KnowledgeGraphWriter) -> None:
    with pytest.raises(ValueError):
        writer.write_identifier({"scheme": "NCT"}, document_uri="doc://1")

    writer.write_identifier(
        {"scheme": "NCT", "value": "1234", "props": "ignored"}, document_uri="doc://1"
    )
    statement = list(writer.statements)[0]
    assert statement.parameters["scheme"] == "NCT"


def test_write_relationship_defaults(writer: KnowledgeGraphWriter) -> None:
    writer.write_relationship("SIMILAR_TO", "chunk-1", "chunk-2")
    statement = list(writer.statements)[0]
    assert "SIMILAR_TO" in statement.cypher
    assert statement.parameters == {"start_value": "chunk-1", "end_value": "chunk-2"}


def test_clear_resets_statements(writer: KnowledgeGraphWriter) -> None:
    writer.write_document({"uri": "doc://1", "id": "doc-1"})
    assert list(writer.statements)
    writer.clear()
    assert list(writer.statements) == []


def test_write_evidence_and_generated_by(writer: KnowledgeGraphWriter) -> None:
    writer.write_evidence(
        {"id": "e-1", "confidence": 0.9},
        outcome_id="out-1",
        variable_id="var-1",
        study_nct_id="nct-1",
        extraction_activity_id="activity-1",
    )
    writer.link_generated_by("Evidence", "e-1", "activity-1")
    statements = list(writer.statements)
    assert any("MEASURES" in stmt.cypher for stmt in statements)
    assert any("WAS_GENERATED_BY" in stmt.cypher for stmt in statements)


def test_link_generated_by_unknown_label(writer: KnowledgeGraphWriter) -> None:
    with pytest.raises(ValueError, match="Unknown node label"):
        writer.link_generated_by("Unknown", "id", "activity")


def test_write_evidence_variable_links(writer: KnowledgeGraphWriter) -> None:
    writer.write_evidence_variable(
        {"id": "ev-1"},
        document_uri="doc://1",
        extraction_activity_id="activity-1",
    )
    statements = list(writer.statements)
    assert any("REPORTS" in stmt.cypher for stmt in statements)
    assert any("WAS_GENERATED_BY_VAR" in stmt.cypher for stmt in statements)


def test_write_adverse_event_links(writer: KnowledgeGraphWriter) -> None:
    writer.write_adverse_event(
        {"id": "ae-1", "count": 10, "denominator": 100},
        study_nct_id="nct-1",
        arm_id="arm-1",
    )
    statements = list(writer.statements)
    assert any("HAS_AE" in stmt.cypher for stmt in statements)
    assert any("MATCH (a:Arm" in stmt.cypher for stmt in statements)


def test_statements_property_returns_copy(writer: KnowledgeGraphWriter) -> None:
    writer.write_document({"uri": "doc://1", "id": "doc-1"})
    statements = list(writer.statements)
    assert isinstance(statements[0], WriteStatement)
    statements.clear()
    assert list(writer.statements)  # original unchanged


def _execute(writer: KnowledgeGraphWriter, driver: FakeNeo4jDriver) -> None:
    statements = list(writer.statements)

    def _tx(tx: Any) -> None:
        for statement in statements:
            tx.run(statement.cypher, statement.parameters)

    session = driver.session()
    session.write_transaction(_tx)


def test_batch_transaction_rolls_back_on_error(writer: KnowledgeGraphWriter) -> None:
    driver = FakeNeo4jDriver()
    writer.write_document({"uri": "doc://rollback", "id": "doc-rollback"})
    writer.write_relationship(
        "SIMILAR_TO",
        "chunk-start",
        "chunk-end",
        start_label="Chunk",
        end_label="Chunk",
    )
    with pytest.raises(ValueError):
        _execute(writer, driver)
    assert driver.get_node("Document", "doc://rollback") is None


def test_property_updates_remove_nulls() -> None:
    driver = FakeNeo4jDriver()
    writer = KnowledgeGraphWriter()
    writer.write_document(
        {"uri": "doc://update", "id": "doc-update", "title": "Initial", "language": "en"}
    )
    _execute(writer, driver)

    writer = KnowledgeGraphWriter()
    writer.write_document(
        {"uri": "doc://update", "id": "doc-update", "title": None, "language": "fr"}
    )
    _execute(writer, driver)

    node = driver.get_node("Document", "doc://update")
    assert node is not None
    assert node["language"] == "fr"
    assert "title" not in node


def test_constraint_violation_raises(writer: KnowledgeGraphWriter) -> None:
    driver = FakeNeo4jDriver()
    driver.add_unique_constraint("Document", "id")
    writer.write_document({"uri": "doc://one", "id": "conflict"})
    _execute(writer, driver)

    writer = KnowledgeGraphWriter()
    writer.write_document({"uri": "doc://two", "id": "conflict"})
    with pytest.raises(ValueError):
        _execute(writer, driver)
    assert driver.get_node("Document", "doc://two") is None
