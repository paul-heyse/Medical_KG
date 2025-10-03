import pytest

from Medical_KG.kg.service import KgWriteFailure, KgWriteResult, KgWriteService


@pytest.fixture()
def valid_payload() -> dict[str, object]:
    return {
        "nodes": [
            {"label": "Outcome", "id": "out-1", "loinc": "1234-5", "unit_ucum": "mg", "provenance": ["run"]},
            {
                "label": "Evidence",
                "id": "ev-1",
                "unit_ucum": "mg",
                "outcome_loinc": "1234-5",
                "provenance": ["run"],
            },
        ],
        "relationships": [
            {"type": "MEASURES", "start_id": "ev-1", "end_id": "out-1"},
        ],
    }


def test_write_returns_summary(monkeypatch: pytest.MonkeyPatch, valid_payload: dict[str, object]) -> None:
    service = KgWriteService()
    monkeypatch.setattr("Medical_KG.kg.service.validate_shacl", lambda graph: [])
    result = service.write(valid_payload)
    assert isinstance(result, KgWriteResult)
    assert result.written_nodes == 2
    assert result.written_relationships == 1


def test_write_raises_on_validation_error(valid_payload: dict[str, object]) -> None:
    service = KgWriteService()
    invalid = dict(valid_payload)
    invalid["nodes"] = [{"id": "missing"}]
    with pytest.raises(KgWriteFailure) as excinfo:
        service.write(invalid)
    assert excinfo.value.issues


def test_write_raises_on_shacl_error(monkeypatch: pytest.MonkeyPatch, valid_payload: dict[str, object]) -> None:
    service = KgWriteService()
    monkeypatch.setattr(
        "Medical_KG.kg.service.validate_shacl", lambda graph: ["missing provenance"]
    )
    with pytest.raises(KgWriteFailure) as excinfo:
        service.write(valid_payload)
    assert [issue.reason for issue in excinfo.value.issues] == ["missing provenance"]
