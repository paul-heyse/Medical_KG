"""Lightweight terminology resolvers used during clinical extraction."""

from __future__ import annotations

from Medical_KG.facets.models import Code

_DRUG_MAP = {
    "metformin": Code(system="RxCUI", code="6809", display="Metformin", confidence=0.9),
    "enalapril": Code(system="RxCUI", code="3264", display="Enalapril", confidence=0.9),
}

_LAB_MAP = {
    "egfr": Code(
        system="LOINC", code="48642-3", display="Glomerular filtration rate", confidence=0.85
    ),
    "hbA1c": Code(system="LOINC", code="4548-4", display="Hemoglobin A1c", confidence=0.85),
}

_MEDDRA_MAP = {
    "nausea": Code(system="MedDRA", code="10028813", display="Nausea", confidence=0.95),
    "vomiting": Code(system="MedDRA", code="10047700", display="Vomiting", confidence=0.95),
}


def resolve_drug(label: str) -> list[Code]:
    key = label.lower()
    code = _DRUG_MAP.get(key)
    return [code] if code else []


def resolve_lab(name: str) -> list[Code]:
    key = name.lower().replace(" ", "")
    code = _LAB_MAP.get(key)
    return [code] if code else []


def resolve_meddra(term: str) -> list[Code]:
    key = term.lower()
    code = _MEDDRA_MAP.get(key)
    return [code] if code else []


__all__ = ["resolve_drug", "resolve_lab", "resolve_meddra"]
