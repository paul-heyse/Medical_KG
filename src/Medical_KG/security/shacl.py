"""Simplified SHACL validation routines."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


class SHACLError(Exception):
    """Raised when a SHACL rule fails."""


@dataclass(frozen=True, slots=True)
class ShaclIssue:
    message: str
    path: tuple[str, ...] = ()
    shape_id: str | None = None

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.message


def load_shapes(paths: Iterable[Path]) -> list[Mapping[str, object]]:
    shapes: list[Mapping[str, object]] = []
    for path in paths:
        shapes.append(_load_shape(path))
    return shapes


def compose_shapes(*shape_sets: Iterable[Mapping[str, object]]) -> list[Mapping[str, object]]:
    composed: list[Mapping[str, object]] = []
    for shape_set in shape_sets:
        composed.extend(list(shape_set))
    return composed


def validate_shacl(
    graph: Mapping[str, Sequence[Mapping[str, object]]],
    *,
    shapes: Sequence[Mapping[str, object]] | None = None,
) -> list[ShaclIssue]:
    issues: list[ShaclIssue] = []
    for evidence in graph.get("evidence", []):
        unit = evidence.get("unit_ucum")
        if unit is None or not isinstance(unit, str) or not unit.strip():
            issues.append(ShaclIssue(f"Evidence {evidence.get('id')} missing UCUM unit", path=("evidence", str(evidence.get("id")))))
        outcome = evidence.get("outcome_loinc")
        if outcome and "outcome" not in evidence:
            issues.append(ShaclIssue(f"Evidence {evidence.get('id')} missing outcome node", path=("evidence", str(evidence.get("id")), "outcome")))
        spans_value = evidence.get("spans")
        spans = spans_value if isinstance(spans_value, Sequence) else []
        for index, span in enumerate(spans):
            if not isinstance(span, Mapping):
                continue
            start = span.get("start")
            end = span.get("end")
            if not isinstance(start, int) or not isinstance(end, int):
                issues.append(
                    ShaclIssue(
                        f"Evidence {evidence.get('id')} has malformed span",
                        path=("evidence", str(evidence.get("id")), "spans", str(index)),
                    )
                )
                continue
            if start >= end:
                issues.append(
                    ShaclIssue(
                        f"Evidence {evidence.get('id')} has invalid span",
                        path=("evidence", str(evidence.get("id")), "spans", str(index)),
                    )
                )
    for adverse_event in graph.get("adverse_events", []):
        grade = adverse_event.get("grade")
        if grade is not None and grade not in {1, 2, 3, 4, 5}:
            issues.append(ShaclIssue(f"Adverse event {adverse_event.get('id')} grade invalid", path=("adverse_events", str(adverse_event.get("id")))))
    for node in graph.get("constraints", []):
        if not node.get("generated_by"):
            issues.append(ShaclIssue(f"Node {node.get('id')} missing provenance link", path=("constraints", str(node.get("id")))))

    for shape in shapes or ():
        issues.extend(_run_shape(graph, shape))

    return issues


def validate_on_write(graph: Mapping[str, Sequence[Mapping[str, object]]], *, shapes: Sequence[Mapping[str, object]] | None = None) -> None:
    issues = validate_shacl(graph, shapes=shapes)
    if issues:
        raise SHACLError("; ".join(str(issue) for issue in issues))


def _load_shape(path: Path) -> Mapping[str, object]:
    payload = path.read_text(encoding="utf-8").strip()
    required = [segment.strip() for segment in payload.split("\n") if segment.strip()]
    return {"id": path.stem, "required": required}


def _run_shape(graph: Mapping[str, Sequence[Mapping[str, object]]], shape: Mapping[str, object]) -> list[ShaclIssue]:
    issues: list[ShaclIssue] = []
    shape_id = str(shape.get("id", "shape"))
    target = str(shape.get("target", "evidence"))
    required = shape.get("required", [])
    for node in graph.get(target, []):
        for requirement in required:
            if requirement not in node or node.get(requirement) in (None, ""):
                issues.append(
                    ShaclIssue(
                        f"Node {node.get('id')} missing required field {requirement}",
                        path=(target, str(node.get("id")), requirement),
                        shape_id=shape_id,
                    )
                )
    return issues


__all__ = [
    "validate_shacl",
    "validate_on_write",
    "load_shapes",
    "compose_shapes",
    "SHACLError",
    "ShaclIssue",
]
