from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


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
