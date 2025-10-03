from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import load_json_fixture

_MESH = load_json_fixture("mesh_descriptor.json")
_UMLS = load_json_fixture("umls_cui.json")
_LOINC = load_json_fixture("loinc_lookup.json")
_ICD11 = load_json_fixture("icd11_code.json")
_SNOMED = load_json_fixture("snomed_lookup.json")
_RXNAV = load_json_fixture("rxnav_properties.json")


def mesh_descriptor() -> dict[str, Any]:
    return deepcopy(_MESH)


def mesh_descriptor_without_descriptor_id() -> dict[str, Any]:
    payload = mesh_descriptor()
    descriptor = payload.get("descriptor")
    if isinstance(descriptor, dict):
        descriptor.pop("descriptorUI", None)
    return payload


def umls_record() -> dict[str, Any]:
    return deepcopy(_UMLS)


def umls_record_without_optional_fields() -> dict[str, Any]:
    payload = umls_record()
    result = payload.get("result")
    if isinstance(result, dict):
        result.pop("definition", None)
        result.pop("name", None)
    return payload


def loinc_record() -> dict[str, Any]:
    return deepcopy(_LOINC)


def loinc_record_without_display() -> dict[str, Any]:
    payload = loinc_record()
    payload.pop("display", None)
    return payload


def icd11_record() -> dict[str, Any]:
    return deepcopy(_ICD11)


def icd11_record_without_text() -> dict[str, Any]:
    payload = icd11_record()
    payload.pop("title", None)
    payload.pop("definition", None)
    payload.pop("browserUrl", None)
    return payload


def snomed_record() -> dict[str, Any]:
    return deepcopy(_SNOMED)


def snomed_record_without_display() -> dict[str, Any]:
    payload = snomed_record()
    payload.pop("display", None)
    return payload


def rxnav_properties() -> dict[str, Any]:
    return deepcopy(_RXNAV)


__all__ = [
    "mesh_descriptor",
    "mesh_descriptor_without_descriptor_id",
    "umls_record",
    "umls_record_without_optional_fields",
    "loinc_record",
    "loinc_record_without_display",
    "icd11_record",
    "icd11_record_without_text",
    "snomed_record",
    "snomed_record_without_display",
    "rxnav_properties",
]
