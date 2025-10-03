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


def cdc_socrata_record() -> dict[str, Any]:
    return deepcopy(_CDC_SOCRATA)


def uspstf_record() -> dict[str, Any]:
    return deepcopy(_USPSTF)


def openprescribing_record() -> dict[str, Any]:
    return deepcopy(_OPENPRESCRIBING)


def cdc_wonder_xml() -> str:
    return _CDC_WONDER


def who_gho_record() -> dict[str, Any]:
    return deepcopy(_WHO_GHO)


__all__ = [
    "nice_guideline",
    "cdc_socrata_record",
    "uspstf_record",
    "openprescribing_record",
    "cdc_wonder_xml",
    "who_gho_record",
]
