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


def umls_record() -> dict[str, Any]:
    return deepcopy(_UMLS)


def loinc_record() -> dict[str, Any]:
    return deepcopy(_LOINC)


def icd11_record() -> dict[str, Any]:
    return deepcopy(_ICD11)


def snomed_record() -> dict[str, Any]:
    return deepcopy(_SNOMED)


def rxnav_properties() -> dict[str, Any]:
    return deepcopy(_RXNAV)


__all__ = [
    "mesh_descriptor",
    "umls_record",
    "loinc_record",
    "icd11_record",
    "snomed_record",
    "rxnav_properties",
]
