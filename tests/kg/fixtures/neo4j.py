from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, MutableMapping, Sequence

from Medical_KG.kg.writer import NODE_KEYS

_NODE_MATCH = re.compile(r"MATCH \((\w+):(\w+) \{(\w+): \$(\w+)\}\)")
_REL_MATCH = re.compile(r"MERGE \((\w+)\)-\[[^:]*:(\w+)\]->\((\w+)\)")
_SET_PROP = re.compile(r"SET r\.(\w+) = \$(\w+)")


@dataclass(slots=True)
class FakeNeo4jDriver:
    """Minimal in-memory Neo4j driver emulating transactional semantics."""

    unique_constraints: MutableMapping[str, list[tuple[str, ...]]] = field(default_factory=dict)
    _nodes: dict[str, dict[str, dict[str, Any]]] = field(init=False, repr=False)
    _relationships: list[dict[str, Any]] = field(init=False, repr=False)
    _unique_index: dict[str, dict[tuple[str, ...], dict[tuple[Any, ...], str]]] = field(
        init=False, repr=False
    )

    def __post_init__(self) -> None:
        self._nodes: dict[str, dict[str, dict[str, Any]]] = {}
        self._relationships: list[dict[str, Any]] = []
        self._unique_index: dict[str, dict[tuple[str, ...], dict[tuple[Any, ...], str]]] = {}

    def session(self) -> "_FakeSession":
        return _FakeSession(self)

    def add_unique_constraint(self, label: str, *properties: str) -> None:
        constraints = list(self.unique_constraints.get(label, []))
        constraints.append(tuple(properties))
        self.unique_constraints[label] = constraints

    def get_node(self, label: str, key_value: str) -> dict[str, Any] | None:
        return copy.deepcopy(self._nodes.get(label, {}).get(key_value))

    @property
    def relationships(self) -> list[dict[str, Any]]:
        return copy.deepcopy(self._relationships)


@dataclass(slots=True)
class _FakeSession:
    driver: FakeNeo4jDriver

    def write_transaction(self, fn: Any, *args: Any, **kwargs: Any) -> Any:
        transaction = _FakeTransaction(self.driver)
        try:
            result = fn(transaction, *args, **kwargs)
        except Exception:
            transaction.rollback()
            raise
        else:
            transaction.commit()
            return result

    def close(self) -> None:  # pragma: no cover - parity with real driver
        return None


@dataclass(slots=True)
class _FakeTransaction:
    driver: FakeNeo4jDriver
    _pending_nodes: dict[str, dict[str, dict[str, Any]]] = field(init=False, repr=False)
    _pending_relationships: list[dict[str, Any]] = field(init=False, repr=False)
    _unique_index: dict[str, dict[tuple[str, ...], dict[tuple[Any, ...], str]]] = field(
        init=False, repr=False
    )

    def __post_init__(self) -> None:
        self._pending_nodes = copy.deepcopy(self.driver._nodes)
        self._pending_relationships = copy.deepcopy(self.driver._relationships)
        self._unique_index = copy.deepcopy(self.driver._unique_index)

    def run(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> Sequence[Mapping[str, Any]]:
        parameters = dict(parameters or {})
        if statement.strip().startswith("MERGE (n:"):
            self._merge_node(statement, parameters)
            return []
        matches = list(_NODE_MATCH.finditer(statement))
        rel_match = _REL_MATCH.search(statement)
        if matches and rel_match:
            self._merge_relationship(matches, rel_match, statement, parameters)
            return []
        raise ValueError(f"Unsupported Cypher statement: {statement}")

    def commit(self) -> None:
        self.driver._nodes = self._pending_nodes
        self.driver._relationships = self._pending_relationships
        self.driver._unique_index = self._unique_index

    def rollback(self) -> None:
        self._pending_nodes = copy.deepcopy(self.driver._nodes)
        self._pending_relationships = copy.deepcopy(self.driver._relationships)
        self._unique_index = copy.deepcopy(self.driver._unique_index)

    def _merge_node(self, statement: str, parameters: Mapping[str, Any]) -> None:
        label_match = re.search(r"MERGE \(n:(\w+)", statement)
        key_match = re.search(r"\$props\.(\w+)\}", statement)
        if not label_match or not key_match:
            raise ValueError(f"Unable to parse node MERGE: {statement}")
        label = label_match.group(1)
        key = key_match.group(1)
        raw_props = dict(parameters.get("props", {}))
        props = {k: v for k, v in raw_props.items() if v is not None}
        null_keys = [key for key, value in raw_props.items() if value is None]
        if key not in props:
            raise ValueError(f"Payload for {label} missing key '{key}'")
        label_nodes = self._pending_nodes.setdefault(label, {})
        key_value = str(props[key])
        existing = label_nodes.get(key_value, {})
        merged = dict(existing)
        merged.update(props)
        for null_key in null_keys:
            merged.pop(null_key, None)
        for constraint in self._constraints_for(label):
            values = tuple(merged.get(prop) for prop in constraint)
            if None in values:
                continue
            index = self._unique_index.setdefault(label, {}).setdefault(constraint, {})
            owner = index.get(values)
            if owner is None:
                index[values] = key_value
            elif owner != key_value:
                raise ValueError(
                    f"Constraint violation on {label} for fields {constraint}: {json.dumps(values)}"
                )
        label_nodes[key_value] = merged

    def _merge_relationship(
        self,
        node_matches: Iterable[re.Match[str]],
        rel_match: re.Match[str],
        statement: str,
        parameters: Mapping[str, Any],
    ) -> None:
        start_match, end_match = list(node_matches)[:2]
        start_var, start_label, start_key, start_param = start_match.groups()
        end_var, end_label, end_key, end_param = end_match.groups()
        rel_type = rel_match.group(2)
        start_id = str(parameters[start_param])
        end_id = str(parameters[end_param])
        if start_id not in self._pending_nodes.get(start_label, {}):
            raise ValueError(f"Missing start node {start_label}:{start_id}")
        if end_id not in self._pending_nodes.get(end_label, {}):
            raise ValueError(f"Missing end node {end_label}:{end_id}")
        rel_props: Dict[str, Any] = {}
        if "rel_props" in parameters:
            rel_props.update(
                {k: v for k, v in dict(parameters["rel_props"]).items() if v is not None}
            )
        for prop, param in _SET_PROP.findall(statement):
            value = parameters.get(param)
            if value is not None:
                rel_props[prop] = value
            elif prop in rel_props:
                rel_props.pop(prop, None)
        existing = next(
            (
                rel
                for rel in self._pending_relationships
                if rel["type"] == rel_type
                and rel["start"] == (start_label, start_id)
                and rel["end"] == (end_label, end_id)
            ),
            None,
        )
        payload = {
            "type": rel_type,
            "start": (start_label, start_id),
            "end": (end_label, end_id),
            "properties": rel_props,
        }
        if existing:
            existing["properties"].update(rel_props)
        else:
            self._pending_relationships.append(payload)

    def _constraints_for(self, label: str) -> Iterable[tuple[str, ...]]:
        defaults: list[tuple[str, ...]] = []
        key = NODE_KEYS.get(label)
        if key:
            defaults.append((key,))
        return list(self.driver.unique_constraints.get(label, [])) + defaults


def sample_result_records() -> list[dict[str, Any]]:
    """Return a canned Neo4j result for query builder tests."""

    return [
        {"document": {"uri": "doc://1", "title": "Example"}, "score": 0.91},
        {"document": {"uri": "doc://2", "title": "Follow-up"}, "score": 0.88},
    ]


def sample_relationship_records() -> list[dict[str, Any]]:
    """Return sample relationship payloads for graph assertions."""

    return [
        {
            "type": "HAS_CHUNK",
            "start": {"label": "Document", "id": "doc://1"},
            "end": {"label": "Chunk", "id": "chunk-1"},
            "properties": {"order": 1},
        },
        {
            "type": "MEASURES",
            "start": {"label": "Evidence", "id": "ev-1"},
            "end": {"label": "Outcome", "id": "out-1"},
            "properties": {"confidence": 0.9},
        },
    ]


__all__ = ["FakeNeo4jDriver", "sample_relationship_records", "sample_result_records"]
