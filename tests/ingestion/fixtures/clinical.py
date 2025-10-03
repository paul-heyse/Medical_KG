from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import load_json_fixture, load_text_fixture

_CLINICAL_STUDY = load_json_fixture("ctgov_study.json")
_ACCESS_GUDID = load_json_fixture("accessgudid.json")
_OPENFDA_FAERS = load_json_fixture("openfda_faers.json")
_OPENFDA_UDI = load_json_fixture("openfda_udi.json")
_DAILYMED_SPL = load_text_fixture("dailymed_spl.xml")


def clinical_study() -> dict[str, Any]:
    return deepcopy(_CLINICAL_STUDY)


def clinical_study_without_outcomes() -> dict[str, Any]:
    study = clinical_study()
    protocol = study.setdefault("protocolSection", {})
    protocol.setdefault("outcomesModule", {})["primaryOutcomes"] = None
    protocol.setdefault("armsInterventionsModule", {}).pop("arms", None)
    protocol.setdefault("eligibilityModule", {})["eligibilityCriteria"] = None
    protocol.setdefault("descriptionModule", {})["briefSummary"] = ""
    return study


def accessgudid_record() -> dict[str, Any]:
    return deepcopy(_ACCESS_GUDID)


def openfda_faers_record() -> dict[str, Any]:
    payload = deepcopy(_OPENFDA_FAERS["results"][0])
    return payload


def openfda_udi_record() -> dict[str, Any]:
    payload = deepcopy(_OPENFDA_UDI["results"][0])
    return payload


def dailymed_xml() -> str:
    return _DAILYMED_SPL


__all__ = [
    "clinical_study",
    "clinical_study_without_outcomes",
    "accessgudid_record",
    "openfda_faers_record",
    "openfda_udi_record",
    "dailymed_xml",
]
