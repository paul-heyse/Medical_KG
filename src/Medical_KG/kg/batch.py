"""Helpers for generating APOC batch upsert statements."""

from __future__ import annotations

from typing import Mapping


def merge_nodes_statement(label: str, *, batch_size: int = 1000) -> str:
    """Return an APOC `apoc.periodic.iterate` statement for node merges."""

    return (
        "CALL apoc.periodic.iterate("
        "'UNWIND $rows AS row RETURN row', "
        f"'CALL apoc.merge.node([\"{label}\"], row.keys, row.props)', "
        f"{{batchSize: {batch_size}, parallel: false}})"
    )


def merge_relationships_statement(rel_type: str, *, batch_size: int = 1000) -> str:
    """Return an APOC statement that merges relationships in batches."""

    return (
        "CALL apoc.periodic.iterate("
        "'UNWIND $rows AS row RETURN row', "
        f"'CALL apoc.merge.relationship(row.start, \"{rel_type}\", row.rel_props, row.endProps, row.end)', "
        f"{{batchSize: {batch_size}, parallel: false}})"
    )


def transaction_config(max_size: str = "512M") -> Mapping[str, str]:
    """Configuration snippet for Neo4j transaction memory limits."""

    return {"dbms.memory.transaction.max_size": max_size}

