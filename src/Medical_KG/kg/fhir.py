from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping, MutableMapping, Sequence


@dataclass(slots=True)
class FhirResource:
    resource_type: str
    payload: Mapping[str, Any]


class ConceptLexicon:
    """Validates that codes originate from allowed code systems."""

    def __init__(self, vocabulary: Mapping[str, Iterable[str]] | None = None) -> None:
        self._vocabulary = {system: set(codes) for system, codes in (vocabulary or {}).items()}

    def validate(self, system: str, code: str) -> None:
        allowed = self._vocabulary.get(system)
        if allowed is not None and code not in allowed:
            raise ValueError(f"Code {code!r} is not registered for system {system!r}")


class EvidenceExporter:
    """Converts KG nodes into simplified FHIR Evidence resources."""

    def __init__(
        self,
        *,
        lexicon: ConceptLexicon | None = None,
        ucum_codes: Iterable[str] | None = None,
    ) -> None:
        self.lexicon = lexicon or ConceptLexicon()
        self.ucum_codes = set(ucum_codes or {"1", "mg", "g", "kg", "mL"})

    def _validate_ucum(self, unit: str | None) -> None:
        if unit and unit not in self.ucum_codes:
            raise ValueError(f"UCUM code {unit!r} is not supported")

    def export_evidence(self, node: Mapping[str, Any]) -> FhirResource:
        unit = node.get("unit_ucum")
        self._validate_ucum(unit)
        statistic = {
            "statisticType": {"coding": [{"code": node.get("type")}]} if node.get("type") else None,
            "value": node.get("value"),
            "sampleSize": node.get("n_total"),
        }
        if unit:
            statistic["unit"] = {"coding": [{"system": "http://unitsofmeasure.org", "code": unit}]}
        ci_low = node.get("ci_low")
        ci_high = node.get("ci_high")
        if ci_low is not None and ci_high is not None:
            statistic["confidenceInterval"] = {"low": ci_low, "high": ci_high}
        statistic = {key: value for key, value in statistic.items() if value is not None}

        payload = {
            "resourceType": "Evidence",
            "id": node.get("id"),
            "status": "active",
            "description": node.get("description"),
            "statistic": [statistic],
            "note": node.get("notes", []),
        }
        return FhirResource(resource_type="Evidence", payload=payload)

    def export_evidence_variable(self, node: Mapping[str, Any]) -> FhirResource:
        characteristics = []
        for entry in node.get("characteristic", []):
            concept = entry.get("concept")
            if concept:
                system = concept.get("system")
                code = concept.get("code")
                if system and code:
                    self.lexicon.validate(system, code)
            characteristics.append(entry)
        payload = {
            "resourceType": "EvidenceVariable",
            "id": node.get("id"),
            "name": node.get("name"),
            "status": "active",
            "characteristic": characteristics,
        }
        return FhirResource(resource_type="EvidenceVariable", payload=payload)

    def export_provenance(
        self,
        extraction_activity: Mapping[str, Any],
        *,
        target_reference: str,
    ) -> FhirResource:
        agent = {
            "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/provenance-participant-type", "code": "author"}]},
            "who": {"display": extraction_activity.get("model")},
        }
        payload = {
            "resourceType": "Provenance",
            "target": [{"reference": target_reference}],
            "recorded": extraction_activity.get("timestamp"),
            "activity": {"display": extraction_activity.get("prompt_hash")},
            "agent": [agent],
        }
        return FhirResource(resource_type="Provenance", payload=payload)


@dataclass(slots=True)
class GraphMapping:
    """Simple container describing nodes and relationships for KG writes."""

    nodes: list[dict[str, Any]]
    relationships: list[dict[str, Any]]


class FhirGraphMapper:
    """Map core FHIR resources into graph-friendly dictionaries."""

    def __init__(self, *, lexicon: ConceptLexicon | None = None) -> None:
        self.lexicon = lexicon or ConceptLexicon()

    def map_patient(self, patient: Mapping[str, Any]) -> GraphMapping:
        patient_id = str(patient.get("id"))
        identifiers = patient.get("identifier", [])
        patient_node: dict[str, Any] = {
            "label": "Patient",
            "id": patient_id,
            "gender": patient.get("gender"),
            "birth_date": patient.get("birthDate"),
            "extensions": patient.get("extension", []),
            "identifier_values": [identifier.get("value") for identifier in identifiers if identifier.get("value")],
        }
        nodes: list[dict[str, Any]] = [patient_node]
        relationships: list[dict[str, Any]] = []
        for identifier in identifiers:
            value = identifier.get("value")
            if not value:
                continue
            system = identifier.get("system") or ""
            identifier_id = f"{system}|{value}" if system else value
            nodes.append(
                {
                    "label": "Identifier",
                    "id": identifier_id,
                    "system": system or None,
                    "value": value,
                }
            )
            relationships.append(
                {
                    "type": "HAS_IDENTIFIER",
                    "start_id": patient_id,
                    "end_id": identifier_id,
                    "properties": {},
                }
            )
        return GraphMapping(nodes=nodes, relationships=relationships)

    def map_condition(self, condition: Mapping[str, Any]) -> GraphMapping:
        condition_id = str(condition.get("id"))
        codes = self._extract_codes(condition.get("code"))
        node = {
            "label": "Condition",
            "id": condition_id,
            "codes": codes,
            "severity": self._code_as_dict(condition.get("severity")),
            "clinical_status": self._code_as_dict(condition.get("clinicalStatus")),
        }
        relationships = self._subject_relationship(condition, condition_id, "HAS_CONDITION")
        return GraphMapping(nodes=[node], relationships=relationships)

    def map_medication_statement(self, statement: Mapping[str, Any]) -> GraphMapping:
        statement_id = str(statement.get("id"))
        dosage = self._parse_dosage(statement.get("dosage", []))
        node = {
            "label": "MedicationStatement",
            "id": statement_id,
            "codes": self._extract_codes(statement.get("medicationCodeableConcept")),
            "status": statement.get("status"),
            "dosage": dosage,
            "effective_period": statement.get("effectivePeriod"),
        }
        relationships = self._subject_relationship(statement, statement_id, "HAS_MEDICATION")
        return GraphMapping(nodes=[node], relationships=relationships)

    def map_observation(self, observation: Mapping[str, Any]) -> GraphMapping:
        observation_id = str(observation.get("id"))
        quantity = observation.get("valueQuantity", {})
        node = {
            "label": "Observation",
            "id": observation_id,
            "codes": self._extract_codes(observation.get("code")),
            "value": quantity.get("value"),
            "unit": quantity.get("unit"),
            "reference_range": observation.get("referenceRange"),
        }
        relationships = self._subject_relationship(observation, observation_id, "HAS_OBSERVATION")
        return GraphMapping(nodes=[node], relationships=relationships)

    def _subject_relationship(
        self, resource: Mapping[str, Any], target_id: str, rel_type: str
    ) -> list[dict[str, Any]]:
        subject = resource.get("subject") or {}
        reference = subject.get("reference")
        if not reference:
            return []
        return [
            {
                "type": rel_type,
                "start_id": reference,
                "end_id": target_id,
                "properties": {},
            }
        ]

    def _extract_codes(self, concept: Mapping[str, Any] | None) -> list[dict[str, str]]:
        if not concept:
            return []
        codes: list[dict[str, str]] = []
        for coding in concept.get("coding", []):
            system = coding.get("system")
            code = coding.get("code")
            if not system or not code:
                continue
            self.lexicon.validate(system, code)
            entry: MutableMapping[str, str] = {"system": system, "code": code}
            if coding.get("display"):
                entry["display"] = coding["display"]
            codes.append(dict(entry))
        return codes

    def _code_as_dict(self, concept: Mapping[str, Any] | None) -> dict[str, str] | None:
        codes = self._extract_codes(concept) if concept else []
        return codes[0] if codes else None

    def _parse_dosage(self, entries: Sequence[Mapping[str, Any]]) -> Mapping[str, Any] | None:
        if not entries:
            return None
        entry = dict(entries[0])
        return {
            "text": entry.get("text"),
            "timing": entry.get("timing"),
            "route": self._code_as_dict(entry.get("route")),
            "dose_and_rate": entry.get("doseAndRate"),
        }
