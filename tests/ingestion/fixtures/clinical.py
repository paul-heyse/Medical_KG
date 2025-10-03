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


def clinical_study_with_optional_fields() -> dict[str, Any]:
    study = clinical_study()
    protocol = study.setdefault("protocolSection", {})
    status_module = protocol.setdefault("statusModule", {})
    status_module["overallStatus"] = "Recruiting"
    status_module["startDateStruct"] = {"date": "2023-01-01"}
    status_module["completionDateStruct"] = {"date": "2024-01-01"}
    design_module = protocol.setdefault("designModule", {})
    design_module["studyType"] = "Interventional"
    design_module["phases"] = ["Phase 2"]
    design_module["enrollmentInfo"] = {"count": 250}
    sponsor_module = protocol.setdefault("sponsorCollaboratorsModule", {})
    sponsor_module["leadSponsor"] = {"name": "Example Sponsor"}
    outcomes_module = protocol.setdefault("outcomesModule", {})
    outcomes_module["primaryOutcomes"] = [
        {
            "measure": "Mortality",
            "description": "28-day mortality",
            "timeFrame": "28 days",
        }
    ]
    derived = study.setdefault("derivedSection", {})
    derived.setdefault("miscInfoModule", {})["version"] = "2024-01-01"
    return study


def clinical_study_without_optional_fields() -> dict[str, Any]:
    study = clinical_study()
    study.pop("derivedSection", None)
    protocol = study.setdefault("protocolSection", {})
    protocol.pop("statusModule", None)
    design_module = protocol.setdefault("designModule", {})
    design_module.pop("studyType", None)
    design_module.pop("phases", None)
    design_module.pop("enrollmentInfo", None)
    sponsor_module = protocol.get("sponsorCollaboratorsModule")
    if isinstance(sponsor_module, dict):
        sponsor_module.pop("leadSponsor", None)
    outcomes_module = protocol.setdefault("outcomesModule", {})
    outcomes_module.pop("primaryOutcomes", None)
    return study


def accessgudid_record() -> dict[str, Any]:
    return deepcopy(_ACCESS_GUDID)


def accessgudid_record_without_optional_fields() -> dict[str, Any]:
    payload = accessgudid_record()
    udi = payload.get("udi")
    if isinstance(udi, dict):
        udi.pop("brandName", None)
        udi.pop("versionOrModelNumber", None)
        udi.pop("companyName", None)
        udi.pop("deviceDescription", None)
    return payload


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
    "clinical_study_with_optional_fields",
    "clinical_study_without_optional_fields",
    "accessgudid_record",
    "accessgudid_record_without_optional_fields",
    "openfda_faers_record",
    "openfda_udi_record",
    "dailymed_xml",
]
