from __future__ import annotations

import pytest

from Medical_KG.kg.fhir import ConceptLexicon, FhirGraphMapper


@pytest.fixture()
def mapper() -> FhirGraphMapper:
    lexicon = ConceptLexicon(
        {
            "http://loinc.org": {"12345-6", "23456-7"},
            "http://snomed.info/sct": {"111", "222"},
            "http://www.nlm.nih.gov/research/umls/rxnorm": {"555"},
        }
    )
    return FhirGraphMapper(lexicon=lexicon)


def test_map_patient_creates_identifier_relationships(mapper: FhirGraphMapper) -> None:
    patient = {
        "resourceType": "Patient",
        "id": "Patient/p-1",
        "gender": "female",
        "birthDate": "1980-01-01",
        "extension": [{"url": "ethnicity", "valueString": "Hispanic"}],
        "identifier": [
            {"system": "http://hospital", "value": "123"},
            {"value": "historic"},
        ],
    }
    mapping = mapper.map_patient(patient)
    patient_node = next(node for node in mapping.nodes if node["label"] == "Patient")
    assert patient_node["gender"] == "female"
    assert "123" in patient_node["identifier_values"]
    assert len(mapping.relationships) == 2
    assert all(rel["type"] == "HAS_IDENTIFIER" for rel in mapping.relationships)


def test_map_condition_links_to_patient(mapper: FhirGraphMapper) -> None:
    condition = {
        "resourceType": "Condition",
        "id": "Condition/c-1",
        "subject": {"reference": "Patient/p-1"},
        "code": {
            "coding": [{"system": "http://snomed.info/sct", "code": "111", "display": "Asthma"}]
        },
        "severity": {"coding": [{"system": "http://snomed.info/sct", "code": "222"}]},
        "clinicalStatus": {"coding": [{"system": "http://snomed.info/sct", "code": "111"}]},
    }
    mapping = mapper.map_condition(condition)
    assert mapping.nodes[0]["codes"][0]["code"] == "111"
    assert mapping.relationships == [
        {
            "type": "HAS_CONDITION",
            "start_id": "Patient/p-1",
            "end_id": "Condition/c-1",
            "properties": {},
        }
    ]


def test_map_medication_statement_captures_dosage(mapper: FhirGraphMapper) -> None:
    statement = {
        "resourceType": "MedicationStatement",
        "id": "MedicationStatement/m-1",
        "status": "active",
        "subject": {"reference": "Patient/p-1"},
        "medicationCodeableConcept": {
            "coding": [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "555",
                    "display": "Example Drug",
                }
            ]
        },
        "effectivePeriod": {"start": "2024-01-01"},
        "dosage": [
            {
                "text": "1 tablet",
                "timing": {"repeat": {"frequency": 1}},
                "route": {"coding": [{"system": "http://snomed.info/sct", "code": "111"}]},
            }
        ],
    }
    mapping = mapper.map_medication_statement(statement)
    node = mapping.nodes[0]
    assert node["dosage"]["text"] == "1 tablet"
    assert mapping.relationships[0]["type"] == "HAS_MEDICATION"


def test_map_observation_records_values(mapper: FhirGraphMapper) -> None:
    observation = {
        "resourceType": "Observation",
        "id": "Observation/o-1",
        "subject": {"reference": "Patient/p-1"},
        "code": {"coding": [{"system": "http://loinc.org", "code": "12345-6"}]},
        "valueQuantity": {"value": 4.2, "unit": "mg/dL"},
        "referenceRange": [{"low": {"value": 3.0}, "high": {"value": 5.0}}],
    }
    mapping = mapper.map_observation(observation)
    node = mapping.nodes[0]
    assert node["value"] == 4.2
    assert node["unit"] == "mg/dL"
    assert mapping.relationships[0]["type"] == "HAS_OBSERVATION"


def test_invalid_codeable_concept_raises(mapper: FhirGraphMapper) -> None:
    with pytest.raises(ValueError):
        mapper.map_condition(
            {
                "id": "Condition/c-2",
                "subject": {"reference": "Patient/p-1"},
                "code": {"coding": [{"system": "http://snomed.info/sct", "code": "999"}]},
            }
        )
