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
        spans_value = evidence.get("spans")
        spans = spans_value if isinstance(spans_value, Sequence) else []
        for span in spans:
            if not isinstance(span, Mapping):
                continue
            start = span.get("start")
            end = span.get("end")
            if not isinstance(start, int) or not isinstance(end, int):
                errors.append(f"Evidence {evidence.get('id')} has malformed span")
                continue
            if start >= end:
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
