from __future__ import annotations

from Medical_KG.kg import batch


def test_merge_nodes_statement_uses_label_and_batch_size() -> None:
    statement = batch.merge_nodes_statement("Condition", batch_size=250)
    assert "apoc.merge.node" in statement
    assert "\"Condition\"" in statement
    assert "batchSize: 250" in statement


def test_merge_relationships_statement_formats_relationship_type() -> None:
    statement = batch.merge_relationships_statement("TREATS", batch_size=500)
    assert "apoc.merge.relationship" in statement
    assert "\"TREATS\"" in statement
    assert "batchSize: 500" in statement


def test_transaction_config_returns_mapping() -> None:
    config = batch.transaction_config("128M")
    assert config == {"dbms.memory.transaction.max_size": "128M"}
