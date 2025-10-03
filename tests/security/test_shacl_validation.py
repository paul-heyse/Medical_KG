from __future__ import annotations

from pathlib import Path

import pytest

from Medical_KG.security import (
    ShaclIssue,
    compose_shapes,
    load_shapes,
    validate_on_write,
    validate_shacl,
)
from Medical_KG.security import shacl as shacl_module


def test_shacl_detects_errors_with_paths() -> None:
    graph = {
        "evidence": [
            {"id": "e1", "outcome_loinc": "1234-5", "spans": [{"start": 5, "end": 1}, "bad"]},
            {"id": "e2", "unit_ucum": "", "spans": [{"start": "x", "end": 10}]},
        ],
        "adverse_events": [{"id": "ae1", "grade": 7}],
        "constraints": [{"id": "c1"}],
    }
    issues = validate_shacl(graph)
    messages = {issue.message for issue in issues}
    assert any("missing UCUM" in message for message in messages)
    assert any(isinstance(issue, ShaclIssue) and issue.path for issue in issues)

    with pytest.raises(Exception):
        validate_on_write(graph)


def test_custom_shapes_loaded(tmp_path: Path) -> None:
    shape1 = tmp_path / "shape1.txt"
    shape1.write_text("required_field", encoding="utf-8")
    shape2 = tmp_path / "shape2.txt"
    shape2.write_text("field_a\nfield_b", encoding="utf-8")

    shapes = compose_shapes(load_shapes([shape1]), load_shapes([shape2]))
    graph = {"evidence": [{"id": "e1", "required_field": "value", "field_a": "", "field_b": "ok"}]}
    issues = validate_shacl(graph, shapes=shapes)
    assert any("field_a" in issue.message for issue in issues)
    assert any(issue.shape_id == "shape2" for issue in issues)


def test_validation_success() -> None:
    graph = {
        "evidence": [
            {
                "id": "e1",
                "unit_ucum": "mg",
                "outcome_loinc": "1234-5",
                "outcome": {"id": "o1"},
                "spans": [{"start": 0, "end": 5}],
            }
        ],
        "adverse_events": [{"id": "ae1", "grade": 3}],
        "constraints": [{"id": "c1", "generated_by": "act-1"}],
    }
    issues = validate_shacl(graph)
    assert issues == []


def test_validate_on_write_success(tmp_path: Path) -> None:
    shape_path = tmp_path / "shape-required.txt"
    shape_path.write_text("required_field", encoding="utf-8")
    shapes = load_shapes([shape_path])
    graph = {
        "evidence": [
            {"id": "e1", "unit_ucum": "mg", "outcome": {"id": "o1"}, "required_field": "value"}
        ]
    }
    validate_on_write(graph, shapes=shapes)


def test_run_shape_direct(tmp_path: Path) -> None:
    shape = {"id": "shape", "required": ["field"], "target": "nodes"}
    graph = {"nodes": [{"id": "n1"}]}
    issues = shacl_module._run_shape(graph, shape)
    assert any("missing required field" in issue.message for issue in issues)
