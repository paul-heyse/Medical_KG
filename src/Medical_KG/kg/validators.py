from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable, List, Mapping


class KgValidationError(Exception):
    """Raised when the knowledge-graph payload fails validation."""


@dataclass(slots=True)
class ValidationIssue:
    reason: str
    payload_hash: str
    payload: Mapping[str, Any]


class DeadLetterQueue:
    """Collects invalid payloads for later inspection."""

    def __init__(self) -> None:
        self.entries: List[ValidationIssue] = []

    def record(self, reason: str, payload: Mapping[str, Any]) -> ValidationIssue:
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        issue = ValidationIssue(reason=reason, payload_hash=digest, payload=payload)
        self.entries.append(issue)
        return issue


class KgValidator:
    """Performs lightweight SHACL-style validations on KG nodes and relationships."""

    def __init__(self, *, ucum_codes: Iterable[str] | None = None, dead_letter: DeadLetterQueue | None = None) -> None:
        self.ucum_codes = set(ucum_codes or {"1", "mg", "g", "kg", "mL"})
        self.dead_letter = dead_letter or DeadLetterQueue()

    def validate_batch(self, nodes: Iterable[Mapping[str, Any]], relationships: Iterable[Mapping[str, Any]]) -> DeadLetterQueue:
        outcomes_by_id: dict[str, Mapping[str, Any]] = {}
        evidence_by_id: dict[str, Mapping[str, Any]] = {}
        identity_map: dict[tuple[str, str], str] = {}

        for node in nodes:
            label = node.get("label")
            try:
                self.validate_node(node)
            except KgValidationError as exc:
                self.dead_letter.record(str(exc), node)
                continue
            if label == "Outcome":
                outcomes_by_id[str(node.get("id"))] = node
            if label == "Evidence":
                evidence_by_id[str(node.get("id"))] = node
            key = self._identity_key(node)
            if key is not None:
                if key in identity_map and identity_map[key] != str(node.get("id", "")):
                    self.dead_letter.record("Identity conflict detected", node)
                else:
                    identity_map[key] = str(node.get("id", ""))

        for relationship in relationships:
            try:
                self.validate_relationship(relationship)
            except KgValidationError as exc:
                self.dead_letter.record(str(exc), relationship)

        self._validate_code_presence(evidence_by_id, outcomes_by_id, relationships)

        if self.dead_letter.entries:
            raise KgValidationError(f"Knowledge graph validation produced {len(self.dead_letter.entries)} issue(s)")
        return self.dead_letter

    def validate_node(self, node: Mapping[str, Any]) -> None:
        label = node.get("label")
        if not label:
            raise KgValidationError("Node missing label")
        if label in {"Evidence", "Outcome"}:
            self._validate_ucum(node, label)
        if label == "Intervention":
            self._validate_dose(node.get("dose"))
        if label in {"Evidence", "EvidenceVariable", "EligibilityConstraint"}:
            self._ensure_provenance(node)
        if node.get("spans_json"):
            self._validate_spans(node["spans_json"])

    def validate_relationship(self, relationship: Mapping[str, Any]) -> None:
        rel_type = relationship.get("type")
        if not rel_type:
            raise KgValidationError("Relationship missing type")
        if rel_type == "HAS_AE":
            count = relationship.get("count", 0)
            denom = relationship.get("denominator", 0)
            grade = relationship.get("grade")
            if count is not None and count < 0:
                raise KgValidationError("Adverse event count must be non-negative")
            if denom is not None and denom < 0:
                raise KgValidationError("Adverse event denominator must be non-negative")
            if grade is not None and grade not in {1, 2, 3, 4, 5}:
                raise KgValidationError("Adverse event grade must be between 1 and 5")
        if rel_type == "USES_INTERVENTION":
            props = relationship.get("properties") or relationship
            self._validate_dose(props.get("dose"))
        if rel_type == "MENTIONS":
            start = relationship.get("start")
            end = relationship.get("end")
            if start is not None and end is not None and end < start:
                raise KgValidationError("MENTIONS relationship end before start")
        if rel_type == "SIMILAR_TO":
            score = relationship.get("score")
            if score is None or not (0.0 <= score <= 1.0):
                raise KgValidationError("SIMILAR_TO requires a score between 0 and 1")

    def _validate_ucum(self, node: Mapping[str, Any], label: str) -> None:
        unit = node.get("unit_ucum") or node.get("properties", {}).get("unit_ucum")
        if label == "Evidence" and not unit:
            unit = node.get("time_unit_ucum")
        if unit and unit not in self.ucum_codes:
            raise KgValidationError(f"Invalid UCUM code: {unit}")

    def _validate_dose(self, dose: Any) -> None:
        if not isinstance(dose, Mapping):
            return
        unit = dose.get("unit") or dose.get("unit_ucum")
        if unit and unit not in self.ucum_codes:
            raise KgValidationError(f"Invalid UCUM code: {unit}")

    def _ensure_provenance(self, node: Mapping[str, Any]) -> None:
        provenance = node.get("provenance") or node.get("properties", {}).get("provenance")
        if not provenance:
            raise KgValidationError("Node missing provenance references")

    def _validate_spans(self, spans: Iterable[Mapping[str, Any]]) -> None:
        span_list = list(spans)
        if not span_list:
            raise KgValidationError("Span list must not be empty")
        for span in span_list:
            start = span.get("start")
            end = span.get("end")
            if start is None or end is None or start < 0 or end < 0 or end < start:
                raise KgValidationError("Invalid span offsets")

    def _validate_code_presence(
        self,
        evidence_nodes: Mapping[str, Mapping[str, Any]],
        outcome_nodes: Mapping[str, Mapping[str, Any]],
        relationships: Iterable[Mapping[str, Any]],
    ) -> None:
        evidence_measure_links: dict[str, str] = {}
        for relationship in relationships:
            if relationship.get("type") == "MEASURES":
                evidence_measure_links[str(relationship.get("start_id"))] = str(relationship.get("end_id"))

        for evidence_id, node in evidence_nodes.items():
            outcome_loinc = node.get("outcome_loinc")
            if not outcome_loinc:
                continue
            linked_outcome_id = evidence_measure_links.get(str(node.get("id", evidence_id)))
            if not linked_outcome_id:
                raise KgValidationError("Evidence node missing MEASURES relationship")
            outcome = outcome_nodes.get(linked_outcome_id)
            if not outcome or outcome.get("loinc") != outcome_loinc:
                raise KgValidationError("Evidence outcome_loinc does not match linked Outcome node")

    def _identity_key(self, node: Mapping[str, Any]) -> tuple[str, str] | None:
        label = node.get("label")
        if label == "Drug" and node.get("rxcui"):
            return ("Drug", str(node["rxcui"]))
        if label == "Device" and node.get("udi_di"):
            return ("Device", str(node["udi_di"]))
        if label == "Concept" and node.get("iri"):
            return ("Concept", str(node["iri"]))
        if label == "Study" and node.get("nct_id"):
            return ("Study", str(node["nct_id"]))
        if label == "Outcome" and node.get("loinc"):
            return ("Outcome", str(node["loinc"]))
        return None
