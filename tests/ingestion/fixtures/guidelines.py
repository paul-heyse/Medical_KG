from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import load_json_fixture, load_text_fixture

_NICE = load_json_fixture("nice_guideline.json")
_CDC_SOCRATA = load_json_fixture("cdc_socrata.json")
_USPSTF = load_json_fixture("uspstf_stub.json")
_OPENPRESCRIBING = load_json_fixture("openprescribing.json")
_CDC_WONDER = load_text_fixture("cdc_wonder.xml")
_WHO_GHO = load_json_fixture("who_gho.json")


def nice_guideline() -> dict[str, Any]:
    return deepcopy(_NICE)


def nice_guideline_with_optional_fields() -> dict[str, Any]:
    guideline = nice_guideline()
    guideline["url"] = guideline.get("url") or "https://example.org/guideline"
    guideline["licence"] = guideline.get("licence") or "OpenGov"
    return guideline


def nice_guideline_without_optional_fields() -> dict[str, Any]:
    guideline = nice_guideline()
    guideline.pop("url", None)
    guideline.pop("licence", None)
    return guideline


def cdc_socrata_record() -> list[dict[str, Any]]:
    return deepcopy(_CDC_SOCRATA)


def cdc_socrata_row() -> dict[str, Any]:
    rows = cdc_socrata_record()
    return deepcopy(rows[0]) if rows else {}


def cdc_socrata_record_with_identifier() -> dict[str, Any]:
    record = cdc_socrata_row()
    record["row_id"] = record.get("row_id") or "CA-2023-EXAMPLE"
    return record


def cdc_socrata_record_without_row_identifier() -> dict[str, Any]:
    record = cdc_socrata_row()
    record.pop("row_id", None)
    return record


def uspstf_record() -> dict[str, Any]:
    return deepcopy(_USPSTF)


def uspstf_record_with_optional_fields() -> dict[str, Any]:
    record = uspstf_record()
    record["id"] = record.get("id") or "USPSTF-2024-A1"
    record["status"] = record.get("status") or "final"
    record["url"] = record.get("url") or "https://example.org/uspstf"
    return record


def uspstf_record_without_optional_fields() -> dict[str, Any]:
    record = uspstf_record()
    record.pop("id", None)
    record.pop("status", None)
    record.pop("url", None)
    return record


def openprescribing_record() -> list[dict[str, Any]]:
    return deepcopy(_OPENPRESCRIBING)


def openprescribing_row() -> dict[str, Any]:
    rows = openprescribing_record()
    return deepcopy(rows[0]) if rows else {}


def openprescribing_record_with_row_identifier() -> dict[str, Any]:
    record = openprescribing_row()
    record["row_id"] = record.get("row_id") or "practice-123"
    return record


def openprescribing_record_without_row_identifier() -> dict[str, Any]:
    record = openprescribing_row()
    record.pop("row_id", None)
    return record


def cdc_wonder_xml() -> str:
    return _CDC_WONDER


def cdc_wonder_xml_without_rows() -> str:
    return "<response></response>"


def who_gho_record() -> dict[str, Any]:
    return deepcopy(_WHO_GHO)


def who_gho_record_with_optional_fields() -> dict[str, Any]:
    record = who_gho_record()
    record["Indicator"] = record.get("Indicator") or "HIV_PREV"
    record["SpatialDim"] = record.get("SpatialDim") or "USA"
    record["TimeDim"] = record.get("TimeDim") or "2024"
    return record


def who_gho_record_without_optional_fields() -> dict[str, Any]:
    record = who_gho_record()
    record.pop("Indicator", None)
    record.pop("SpatialDim", None)
    record.pop("TimeDim", None)
    return record


__all__ = [
    "nice_guideline",
    "nice_guideline_with_optional_fields",
    "nice_guideline_without_optional_fields",
    "cdc_socrata_record",
    "cdc_socrata_row",
    "cdc_socrata_record_with_identifier",
    "cdc_socrata_record_without_row_identifier",
    "uspstf_record",
    "uspstf_record_with_optional_fields",
    "uspstf_record_without_optional_fields",
    "openprescribing_record",
    "openprescribing_row",
    "openprescribing_record_with_row_identifier",
    "openprescribing_record_without_row_identifier",
    "cdc_wonder_xml",
    "cdc_wonder_xml_without_rows",
    "who_gho_record",
    "who_gho_record_with_optional_fields",
    "who_gho_record_without_optional_fields",
]
