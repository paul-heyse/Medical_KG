import pytest

from Medical_KG.kg.fhir import ConceptLexicon, EvidenceExporter
from Medical_KG.kg.query import KgQueryApi


def test_evidence_exporter_builds_payload() -> None:
    exporter = EvidenceExporter(ucum_codes={"mg"})
    node = {
        "id": "ev-1",
        "type": "risk-ratio",
        "value": 1.2,
        "n_total": 120,
        "unit_ucum": "mg",
        "ci_low": 0.9,
        "ci_high": 1.4,
        "description": "Risk ratio",
        "notes": ["example"],
    }
    resource = exporter.export_evidence(node)
    assert resource.resource_type == "Evidence"
    statistic = resource.payload["statistic"][0]
    assert statistic["unit"]["coding"][0]["code"] == "mg"


def test_evidence_variable_validates_codes() -> None:
    lexicon = ConceptLexicon({"http://snomed.info/sct": {"123"}})
    exporter = EvidenceExporter(lexicon=lexicon)
    node = {
        "id": "var-1",
        "name": "Condition",
        "characteristic": [{"concept": {"system": "http://snomed.info/sct", "code": "123"}}],
    }
    resource = exporter.export_evidence_variable(node)
    assert resource.payload["characteristic"]
    with pytest.raises(ValueError):
        exporter.export_evidence_variable(
            {
                "id": "var-2",
                "name": "Condition",
                "characteristic": [
                    {"concept": {"system": "http://snomed.info/sct", "code": "999"}},
                ],
            }
        )


def test_query_helpers_return_parameters() -> None:
    api = KgQueryApi()
    related = api.related_evidence(drug_label="Warfarin", condition_label="AF", limit=5)
    assert "MATCH (drug:Concept" in related.cypher
    assert related.parameters == {"drug_label": "Warfarin", "condition_label": "AF", "limit": 5}

    subsumption = api.subsumption_evidence(condition_label="Diabetes", max_depth=2)
    assert "IS_A*0..2" in subsumption.cypher
    assert subsumption.parameters == {"condition_label": "Diabetes"}

    provenance = api.provenance_trace(evidence_id="e-1")
    assert "WAS_GENERATED_BY" in provenance.cypher
    assert provenance.parameters == {"evidence_id": "e-1"}

    vector = api.vector_search(index_name="chunk_idx", query_vector=[0.1, 0.2], top_k=3)
    assert "db.index.vector.queryNodes" in vector.cypher
    assert vector.parameters["top_k"] == 3
