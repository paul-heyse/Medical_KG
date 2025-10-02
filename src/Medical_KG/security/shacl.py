"""Simplified SHACL validation routines."""
from __future__ import annotations

from typing import Iterable, Mapping, Sequence


class SHACLError(Exception):
    """Raised when a SHACL rule fails."""


def validate_shacl(graph: Mapping[str, Sequence[Mapping[str, object]]]) -> list[str]:
    errors: list[str] = []
    for evidence in graph.get("evidence", []):
        unit = evidence.get("unit_ucum")
        if unit is None or not isinstance(unit, str) or not unit.strip():
            errors.append(f"Evidence {evidence.get('id')} missing UCUM unit")
        outcome = evidence.get("outcome_loinc")
        if outcome and "outcome" not in evidence:
            errors.append(f"Evidence {evidence.get('id')} missing outcome node")
        spans = evidence.get("spans") or []
        for span in spans:
            if span["start"] >= span["end"]:
                errors.append(f"Evidence {evidence.get('id')} has invalid span")
    for adverse_event in graph.get("adverse_events", []):
        grade = adverse_event.get("grade")
        if grade is not None and grade not in {1, 2, 3, 4, 5}:
            errors.append(f"Adverse event {adverse_event.get('id')} grade invalid")
    for node in graph.get("constraints", []):
        if not node.get("generated_by"):
            errors.append(f"Node {node.get('id')} missing provenance link")
    return errors


__all__ = ["validate_shacl", "SHACLError"]
