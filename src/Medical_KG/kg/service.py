"""High-level helpers for validating and committing knowledge-graph writes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, Sequence

from Medical_KG.kg.validators import KgValidationError, KgValidator, ValidationIssue
from Medical_KG.security.shacl import validate_shacl


@dataclass(slots=True)
class KgWriteResult:
    """Summary of a successful KG write."""

    written_nodes: int
    written_relationships: int


class KgWriteFailure(Exception):
    """Raised when KG payload fails schema or SHACL validation."""

    def __init__(self, issues: Sequence[ValidationIssue]):
        super().__init__("Knowledge graph validation failed")
        self.issues = list(issues)


class KgWriteService:
    """Validate KG payloads via structural and SHACL checks before commit."""

    def __init__(self, *, ucum_codes: Iterable[str] | None = None) -> None:
        self._ucum_codes = tuple(ucum_codes) if ucum_codes else None

    def write(self, payload: Mapping[str, Any]) -> KgWriteResult:
        nodes = [dict(node) for node in payload.get("nodes", [])]
        relationships = [dict(rel) for rel in payload.get("relationships", [])]

        validator = KgValidator(ucum_codes=self._ucum_codes)
        try:
            validator.validate_batch(nodes, relationships)
        except KgValidationError as exc:
            raise KgWriteFailure(list(validator.dead_letter.entries)) from exc

        graph_payload = self._build_shacl_graph(nodes, payload.get("graph"))
        errors = validate_shacl(graph_payload)
        if errors:
            for error in errors:
                validator.dead_letter.record(
                    str(error), {"graph": graph_payload, "path": getattr(error, "path", ())}
                )
            raise KgWriteFailure(list(validator.dead_letter.entries))

        return KgWriteResult(written_nodes=len(nodes), written_relationships=len(relationships))

    def _build_shacl_graph(
        self,
        nodes: Sequence[Mapping[str, Any]],
        explicit_graph: Mapping[str, Sequence[Mapping[str, Any]]] | None,
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        if explicit_graph:
            return explicit_graph
        evidence: list[Mapping[str, Any]] = []
        adverse_events: list[Mapping[str, Any]] = []
        constraints: list[Mapping[str, Any]] = []
        for node in nodes:
            label = str(node.get("label", ""))
            if label == "Evidence":
                evidence.append(node)
            elif label == "AdverseEvent":
                adverse_events.append(node)
            elif label in {"EligibilityConstraint", "EvidenceVariable", "ExtractionActivity"}:
                constraints.append(node)
        return {"evidence": evidence, "adverse_events": adverse_events, "constraints": constraints}


__all__ = ["KgWriteService", "KgWriteResult", "KgWriteFailure"]
