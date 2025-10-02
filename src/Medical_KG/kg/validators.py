from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


class KgValidationError(Exception):
    pass


@dataclass(slots=True)
class ValidationIssue:
    node_id: str
    reason: str


class KgValidator:
    """Lightweight validator emulating SHACL rules."""

    def __init__(self, *, ucum_codes: Iterable[str] | None = None) -> None:
        self.ucum_codes = set(ucum_codes or {"1", "mg", "kg", "mL"})

    def validate_ucum(self, node: Mapping[str, Any]) -> None:
        unit = node.get("unit_ucum") or node.get("unit")
        if unit and unit not in self.ucum_codes:
            raise KgValidationError(f"Invalid UCUM code: {unit}")

    def validate_spans(self, node: Mapping[str, Any]) -> None:
        spans = node.get("spans_json")
        if spans:
            for span in spans:
                start = span.get("start")
                end = span.get("end")
                length = span.get("length", 0)
                if start is None or end is None or start < 0 or end < 0 or end < start:
                    raise KgValidationError("Invalid span offsets")
                if length and end - start != length:
                    raise KgValidationError("Span length mismatch")
        else:
            raise KgValidationError("spans_json missing or empty")

    def ensure_provenance(self, node: Mapping[str, Any]) -> None:
        provenance = node.get("provenance", [])
        if not provenance:
            raise KgValidationError("Node missing provenance references")

    def validate_relationship(self, relationship: Mapping[str, Any]) -> None:
        if relationship.get("type") == "HAS_AE":
            count = relationship.get("count", 0)
            if count < 0:
                raise KgValidationError("Adverse event count must be non-negative")
            grade = relationship.get("grade")
            if grade is not None and grade not in {1, 2, 3, 4, 5}:
                raise KgValidationError("Grade must be between 1 and 5")

    def validate_node(self, node: Mapping[str, Any]) -> None:
        label = node.get("label")
        if label in {"Evidence", "Outcome"}:
            self.validate_ucum(node)
        if label in {"Evidence", "EvidenceVariable", "EligibilityConstraint"}:
            self.ensure_provenance(node)
        if "spans_json" in node:
            self.validate_spans(node)
