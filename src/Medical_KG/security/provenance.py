"""PROV provenance tracking."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Iterable, Mapping


@dataclass(frozen=True, slots=True)
class ExtractionActivity:
    activity_id: str
    model: str
    version: str
    prompt_hash: str
    schema_hash: str
    timestamp: datetime


class ProvenanceStore:
    """Maintains provenance links between assertions and extraction activities."""

    def __init__(self) -> None:
        self._activities: Dict[str, ExtractionActivity] = {}
        self._links: Dict[str, str] = {}
        self._derivations: Dict[str, set[str]] = {}

    def register_activity(self, activity: ExtractionActivity) -> None:
        self._activities[activity.activity_id] = activity

    def link_assertion(self, assertion_id: str, activity_id: str) -> None:
        if activity_id not in self._activities:
            raise KeyError(f"Unknown activity {activity_id}")
        self._links[assertion_id] = activity_id

    def activity_for(self, assertion_id: str) -> ExtractionActivity:
        activity_id = self._links.get(assertion_id)
        if activity_id is None:
            raise KeyError(f"Assertion {assertion_id} missing provenance")
        return self._activities[activity_id]

    def metadata(self) -> Mapping[str, Mapping[str, object]]:
        return {
            assertion_id: {
                "activity_id": activity.activity_id,
                "model": activity.model,
                "version": activity.version,
            }
            for assertion_id, activity in (
                (assertion_id, self._activities[activity_id])
                for assertion_id, activity_id in self._links.items()
            )
        }

    def trace_lineage(self, assertion_id: str) -> list[str]:
        lineage: list[str] = [assertion_id]
        visited = set(lineage)
        queue = [assertion_id]
        while queue:
            current = queue.pop()
            parents = self._derivations.get(current, set())
            for parent in parents:
                if parent not in visited:
                    lineage.append(parent)
                    visited.add(parent)
                    queue.append(parent)
        return lineage

    def record_derivation(self, child_id: str, parent_id: str) -> None:
        bucket = self._derivations.setdefault(child_id, set())
        bucket.add(parent_id)

    def prov_o(self) -> Mapping[str, object]:
        entities = {assertion: {"prov:wasGeneratedBy": link} for assertion, link in self._links.items()}
        activities = {
            activity_id: {
                "prov:type": "Extraction",
                "prov:startedAtTime": activity.timestamp.isoformat(),
                "prov:usedModel": activity.model,
            }
            for activity_id, activity in self._activities.items()
        }
        derivations = [
            {"prov:generatedEntity": child, "prov:usedEntity": parent}
            for child, parents in self._derivations.items()
            for parent in parents
        ]
        return {
            "@context": {"prov": "http://www.w3.org/ns/prov#"},
            "entity": entities,
            "activity": activities,
            "wasDerivedFrom": derivations,
        }

    def as_graph(self) -> Mapping[str, Iterable[str]]:
        graph: Dict[str, set[str]] = {}
        for child, parents in self._derivations.items():
            graph.setdefault(child, set()).update(parents)
        return {node: tuple(sorted(parents)) for node, parents in graph.items()}


__all__ = ["ExtractionActivity", "ProvenanceStore"]
