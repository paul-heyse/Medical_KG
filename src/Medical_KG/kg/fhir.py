from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(slots=True)
class FhirResource:
    resource_type: str
    payload: Mapping[str, Any]


class EvidenceExporter:
    """Converts KG nodes to simplified FHIR resources."""

    def export_evidence(self, node: Mapping[str, Any]) -> FhirResource:
        statistic = {
            "statisticType": node.get("type"),
            "value": node.get("value"),
            "sampleSize": node.get("n_total"),
        }
        if node.get("ci_low") is not None and node.get("ci_high") is not None:
            statistic["confidenceInterval"] = {
                "low": node["ci_low"],
                "high": node["ci_high"],
            }
        payload = {
            "resourceType": "Evidence",
            "id": node.get("id"),
            "status": "active",
            "variableDefinition": node.get("variables", []),
            "statistic": [statistic],
            "note": node.get("notes", []),
        }
        return FhirResource(resource_type="Evidence", payload=payload)

    def export_evidence_variable(self, node: Mapping[str, Any]) -> FhirResource:
        payload = {
            "resourceType": "EvidenceVariable",
            "id": node.get("id"),
            "name": node.get("name"),
            "status": "active",
            "characteristic": node.get("characteristic", []),
        }
        return FhirResource(resource_type="EvidenceVariable", payload=payload)
