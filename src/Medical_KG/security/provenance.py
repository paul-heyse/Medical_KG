"""PROV provenance tracking."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Mapping


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


__all__ = ["ExtractionActivity", "ProvenanceStore"]
