import pytest

from Medical_KG.kg.validators import DeadLetterQueue, KgValidationError, KgValidator


def make_valid_payload() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    nodes = [
        {
            "label": "Outcome",
            "id": "out-1",
            "loinc": "1234-5",
            "unit_ucum": "mg",
            "provenance": ["activity"],
        },
        {
            "label": "Evidence",
            "id": "ev-1",
            "unit_ucum": "mg",
            "outcome_loinc": "1234-5",
            "provenance": ["activity"],
        },
    ]
    relationships = [
        {"type": "MEASURES", "start_id": "ev-1", "end_id": "out-1"},
    ]
    return nodes, relationships


def test_validate_batch_success() -> None:
    nodes, relationships = make_valid_payload()
    validator = KgValidator(ucum_codes={"mg"})
    dead_letter = validator.validate_batch(nodes, relationships)
    assert dead_letter.entries == []


def test_validate_node_missing_label_records_issue() -> None:
    validator = KgValidator(ucum_codes={"mg"})
    nodes, relationships = make_valid_payload()
    nodes.append({"label": "Evidence", "id": "ev-2", "unit_ucum": "mg", "provenance": ["activity"]})
    nodes.append({"id": "missing"})
    with pytest.raises(KgValidationError):
        validator.validate_batch(nodes, relationships)
    assert any("missing label" in issue.reason.lower() for issue in validator.dead_letter.entries)


def test_validate_relationship_rules() -> None:
    validator = KgValidator(ucum_codes={"mg"})
    with pytest.raises(KgValidationError):
        validator.validate_relationship({"type": "HAS_AE", "count": -1})
    with pytest.raises(KgValidationError):
        validator.validate_relationship({"type": "SIMILAR_TO", "score": 2})
    with pytest.raises(KgValidationError):
        validator.validate_relationship({"type": "MENTIONS", "start": 10, "end": 5})


def test_validate_batch_detects_missing_measures_relationship() -> None:
    nodes, relationships = make_valid_payload()
    relationships.clear()
    validator = KgValidator(ucum_codes={"mg"})
    with pytest.raises(KgValidationError, match="MEASURES relationship"):
        validator.validate_batch(nodes, relationships)


def test_dead_letter_records_hash() -> None:
    queue = DeadLetterQueue()
    issue = queue.record("reason", {"foo": "bar"})
    assert len(issue.payload_hash) == 64
    assert queue.entries == [issue]
