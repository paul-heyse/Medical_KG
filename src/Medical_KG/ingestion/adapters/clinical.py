from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator, Iterable
from typing import Mapping, Sequence

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.adapters.http import HttpAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.types import (
    AccessGudidDocumentPayload,
    ClinicalDocumentPayload,
    ClinicalTrialsStudyPayload,
    DailyMedDocumentPayload,
    DailyMedSectionPayload,
    JSONMapping,
    JSONValue,
    OpenFdaDocumentPayload,
    RxNormDocumentPayload,
    is_clinical_document_payload,
    narrow_to_mapping,
)
from Medical_KG.ingestion.utils import (
    canonical_json,
    ensure_json_mapping,
    ensure_json_sequence,
    ensure_json_value,
    normalize_text,
)

_CT_NCT_RE = re.compile(r"^NCT\d{8}$")
_GTIN14_RE = re.compile(r"^\d{14}$")


class ClinicalTrialsGovAdapter(HttpAdapter[ClinicalTrialsStudyPayload]):
    """Adapter for ClinicalTrials.gov v2 API."""

    source = "clinicaltrials"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        api_base: str = "https://clinicaltrials.gov/api/v2",
        bootstrap_records: Iterable[ClinicalTrialsStudyPayload] | None = None,
    ) -> None:
        super().__init__(context, client)
        self.api_base = api_base.rstrip("/")
        self._bootstrap: list[ClinicalTrialsStudyPayload] = list(bootstrap_records or [])

    async def fetch(self, *_: object, **__: object) -> AsyncIterator[ClinicalTrialsStudyPayload]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        page_token: str | None = None
        while True:
            params: dict[str, object] = {"pageSize": 100}
            if page_token:
                params["pageToken"] = page_token
            payload = await self.fetch_json(f"{self.api_base}/studies", params=params)
            payload_map = ensure_json_mapping(payload, context="clinicaltrials response")
            studies_value = payload_map.get("studies", [])
            for study_value in ensure_json_sequence(studies_value, context="clinicaltrials studies"):
                study_map = ensure_json_mapping(study_value, context="clinicaltrials study")
                protocol_section = ensure_json_mapping(
                    study_map.get("protocolSection"),
                    context="clinicaltrials protocolSection",
                )
                study_payload: ClinicalTrialsStudyPayload = {
                    "protocolSection": dict(protocol_section),
                }
                derived_section_value = study_map.get("derivedSection")
                if isinstance(derived_section_value, Mapping):
                    study_payload["derivedSection"] = dict(
                        ensure_json_mapping(
                            derived_section_value,
                            context="clinicaltrials derivedSection",
                        )
                    )
                yield study_payload
            next_token_value = payload_map.get("nextPageToken")
            page_token = next_token_value if isinstance(next_token_value, str) and next_token_value else None
            if not page_token:
                break

    def parse(self, raw: ClinicalTrialsStudyPayload) -> Document:
        protocol = ensure_json_mapping(
            raw.get("protocolSection"),
            context="clinicaltrials protocol",
        )
        identification = ensure_json_mapping(
            protocol.get("identificationModule", {}),
            context="clinicaltrials identification",
        )
        nct_id = str(identification.get("nctId", ""))
        title = normalize_text(str(identification.get("briefTitle", "")))

        status_module = ensure_json_mapping(
            protocol.get("statusModule", {}),
            context="clinicaltrials status module",
        )
        status_value = status_module.get("overallStatus")
        status = str(status_value) if isinstance(status_value, str) else None

        description_module = ensure_json_mapping(
            protocol.get("descriptionModule", {}),
            context="clinicaltrials description module",
        )
        summary_value = description_module.get("briefSummary", "")
        summary = normalize_text(str(summary_value)) if isinstance(summary_value, str) else ""

        derived_section_value = raw.get("derivedSection")
        derived_section: dict[str, JSONValue] = {}
        if derived_section_value is not None:
            derived_section = dict(
                narrow_to_mapping(
                    derived_section_value,
                    context="clinicaltrials derived section",
                )
            )
        misc_info = ensure_json_mapping(
            derived_section.get("miscInfoModule", {}),
            context="clinicaltrials misc info",
        )
        version = str(misc_info.get("version", "unknown"))

        sponsor_module = ensure_json_mapping(
            protocol.get("sponsorCollaboratorsModule", {}),
            context="clinicaltrials sponsor module",
        )
        lead_sponsor_mapping = ensure_json_mapping(
            sponsor_module.get("leadSponsor", {}),
            context="clinicaltrials lead sponsor",
        )
        lead_sponsor_name_value = lead_sponsor_mapping.get("name")
        lead_sponsor_name = str(lead_sponsor_name_value) if isinstance(lead_sponsor_name_value, str) else None

        design_module = ensure_json_mapping(
            protocol.get("designModule", {}),
            context="clinicaltrials design module",
        )
        phases_value = design_module.get("phases")
        phases: list[str] = []
        if phases_value is not None:
            for phase in ensure_json_sequence(phases_value, context="clinicaltrials phases"):
                if isinstance(phase, str):
                    phases.append(phase)
        phase_text = ", ".join(phases)
        study_type_value = design_module.get("studyType")
        study_type = str(study_type_value) if isinstance(study_type_value, str) else None

        enrollment_info = ensure_json_mapping(
            design_module.get("enrollmentInfo", {}),
            context="clinicaltrials enrollment",
        )
        enrollment_raw = enrollment_info.get("count")
        enrollment: int | str | None
        if isinstance(enrollment_raw, int):
            enrollment = enrollment_raw
        elif isinstance(enrollment_raw, str):
            enrollment = enrollment_raw
        else:
            enrollment = None

        start_date_struct = ensure_json_mapping(
            status_module.get("startDateStruct", {}),
            context="clinicaltrials start date",
        )
        start_date_value = start_date_struct.get("date")
        start_date = str(start_date_value) if isinstance(start_date_value, str) else None

        completion_date_struct = ensure_json_mapping(
            status_module.get("completionDateStruct", {}),
            context="clinicaltrials completion date",
        )
        completion_date_value = completion_date_struct.get("date")
        completion_date = str(completion_date_value) if isinstance(completion_date_value, str) else None

        arms_module = ensure_json_mapping(
            protocol.get("armsInterventionsModule", {}),
            context="clinicaltrials arms module",
        )
        arms_list: list[JSONMapping] = []
        arms_value = arms_module.get("arms")
        if arms_value is not None:
            for arm in ensure_json_sequence(arms_value, context="clinicaltrials arms"):
                arms_list.append(ensure_json_mapping(arm, context="clinicaltrials arm"))

        eligibility_module = ensure_json_mapping(
            protocol.get("eligibilityModule", {}),
            context="clinicaltrials eligibility module",
        )
        eligibility_value = ensure_json_value(
            eligibility_module.get("eligibilityCriteria"),
            context="clinicaltrials eligibility",
        )

        outcomes_module = ensure_json_mapping(
            protocol.get("outcomesModule", {}),
            context="clinicaltrials outcomes module",
        )
        outcomes_value = outcomes_module.get("primaryOutcomes")
        outcomes_list: list[JSONMapping] = []
        if outcomes_value is not None:
            for outcome in ensure_json_sequence(outcomes_value, context="clinicaltrials outcomes"):
                outcomes_list.append(ensure_json_mapping(outcome, context="clinicaltrials outcome"))
        outcomes_payload: Sequence[JSONMapping] | None = outcomes_list if outcomes_list else None

        payload: ClinicalDocumentPayload = {
            "nct_id": nct_id,
            "title": title,
            "status": status,
            "phase": phase_text or None,
            "study_type": study_type,
            "arms": arms_list,
            "eligibility": eligibility_value,
            "version": version,
            "lead_sponsor": lead_sponsor_name,
            "enrollment": enrollment,
            "start_date": start_date,
            "completion_date": completion_date,
        }
        if outcomes_payload is not None:
            payload["outcomes"] = outcomes_payload

        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=nct_id, version=version, content=content)
        metadata: dict[str, JSONValue] = {
            "title": title,
            "record_version": version,
        }
        if status is not None:
            metadata["status"] = status
        if payload["lead_sponsor"]:
            metadata["sponsor"] = payload["lead_sponsor"]
        if payload["phase"]:
            metadata["phase"] = payload["phase"]
        if payload["enrollment"] is not None:
            metadata["enrollment"] = payload["enrollment"]
        if start_date is not None:
            metadata["start_date"] = start_date
        if completion_date is not None:
            metadata["completion_date"] = completion_date
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=summary or title,
            metadata=metadata,
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        raw_payload = document.raw
        if not is_clinical_document_payload(raw_payload):
            raise ValueError("ClinicalTrials document missing typed payload")
        nct_id = raw_payload.get("nct_id")
        if not isinstance(nct_id, str) or not _CT_NCT_RE.match(nct_id):
            raise ValueError(f"Invalid NCT ID: {nct_id}")
        outcomes = raw_payload.get("outcomes", [])
        if outcomes and not isinstance(outcomes, list):
            raise ValueError("Outcomes must be a list")


class OpenFdaAdapter(HttpAdapter[JSONMapping]):
    """Adapter for openFDA resources."""

    source = "openfda"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        api_key: str | None = None,
        bootstrap_records: Iterable[JSONMapping] | None = None,
    ) -> None:
        super().__init__(context, client)
        self.api_key = api_key
        self._bootstrap: list[JSONMapping] = list(bootstrap_records or [])

    async def fetch(
        self,
        resource: str,
        *,
        search: str | None = None,
        limit: int = 100,
    ) -> AsyncIterator[JSONMapping]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        params: dict[str, object] = {"limit": limit}
        if search:
            params["search"] = search
        if self.api_key:
            params["api_key"] = self.api_key
        payload = await self.fetch_json(f"https://api.fda.gov/{resource}.json", params=params)
        payload_map = ensure_json_mapping(payload, context="openfda response")
        results_value = payload_map.get("results", [])
        for record_value in ensure_json_sequence(results_value, context="openfda results"):
            record_map = ensure_json_mapping(record_value, context="openfda record")
            yield dict(record_map)

    def parse(self, raw: JSONMapping) -> Document:
        identifier_value = (
            raw.get("safetyreportid")
            or raw.get("udi_di")
            or raw.get("setid")
            or raw.get("id")
        )
        if identifier_value is None:
            raise ValueError("Record missing identifier")
        identifier = str(identifier_value)
        version_value = raw.get("receivedate") or raw.get("version_number") or raw.get("last_updated")
        version = str(version_value) if version_value else "unknown"
        record_payload: dict[str, JSONValue] = {
            key: ensure_json_value(value, context="openfda record field")
            for key, value in raw.items()
        }
        payload: OpenFdaDocumentPayload = {
            "identifier": identifier,
            "version": version,
            "record": record_payload,
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=identifier, version=version, content=content)
        metadata: dict[str, JSONValue] = {"identifier": identifier}
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps({"identifier": identifier}),
            metadata=metadata,
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        identifier = document.metadata.get("identifier")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("openFDA document missing identifier metadata")


class DailyMedAdapter(HttpAdapter[str]):
    """Adapter for DailyMed SPL documents."""

    source = "dailymed"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[str] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, setid: str) -> AsyncIterator[str]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        params = {"type": "spl", "setid": setid}
        xml = await self.fetch_text("https://dailymed.nlm.nih.gov/dailymed/services/v2/spls", params=params)
        yield xml

    def parse(self, raw: str) -> Document:
        root = ET.fromstring(raw)
        setid_elem = root.find("setid")
        setid_attr = setid_elem.get("root") if setid_elem is not None else None
        setid = str(setid_attr) if isinstance(setid_attr, str) else "unknown"
        title = normalize_text(root.findtext("title", default=""))
        sections: list[DailyMedSectionPayload] = []
        for section in root.findall("section"):
            code_elem = section.find("code")
            loinc_attr = code_elem.get("code") if code_elem is not None else None
            loinc = str(loinc_attr) if isinstance(loinc_attr, str) else None
            text = normalize_text(section.findtext("text", default=""))
            sections.append({"loinc": loinc, "text": text})
        effective = root.find("effectiveTime")
        version_attr = effective.get("value") if effective is not None else None
        version = str(version_attr) if isinstance(version_attr, str) else "unknown"
        payload: DailyMedDocumentPayload = {
            "setid": setid,
            "title": title,
            "version": version,
            "sections": sections,
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=setid, version=version, content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=title,
            metadata={"setid": setid, "version": version},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        setid = document.metadata.get("setid")
        if not isinstance(setid, str) or not setid:
            raise ValueError("DailyMed record missing setid")


class RxNormAdapter(HttpAdapter[JSONMapping]):
    """Adapter for RxNav / RxNorm lookups."""

    source = "rxnorm"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[JSONMapping] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap: list[JSONMapping] = list(bootstrap_records or [])

    async def fetch(self, rxcui: str) -> AsyncIterator[JSONMapping]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json(f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/properties.json")
        yield ensure_json_mapping(payload, context="rxnorm response")

    def parse(self, raw: JSONMapping) -> Document:
        props = ensure_json_mapping(raw.get("properties", {}), context="rxnorm properties")
        rxcui_value = props.get("rxcui")
        if rxcui_value is None:
            raise ValueError("RxNorm payload missing rxcui")
        rxcui = str(rxcui_value)
        name_value = props.get("name")
        synonym_value = props.get("synonym")
        tty_value = props.get("tty")
        ndc_value = props.get("ndc")
        payload: RxNormDocumentPayload = {
            "rxcui": rxcui,
            "name": name_value if isinstance(name_value, str) else None,
            "synonym": synonym_value if isinstance(synonym_value, str) else None,
            "tty": tty_value if isinstance(tty_value, str) else None,
            "ndc": ndc_value if isinstance(ndc_value, str) else None,
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=rxcui, version="v1", content=content)
        display_name = payload.get("name") or ""
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=str(display_name),
            metadata={"rxcui": rxcui},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        rxcui = document.metadata.get("rxcui")
        if not rxcui or not str(rxcui).isdigit():
            raise ValueError("Invalid RxCUI")


class UdiValidator:
    """GTIN-14 validator for device identifiers."""

    @staticmethod
    def validate(value: str) -> bool:
        if not _GTIN14_RE.match(value):
            return False
        digits = [int(c) for c in value]
        checksum = 0
        for index, digit in enumerate(reversed(digits[:-1]), start=1):
            weight = 3 if index % 2 == 1 else 1
            checksum += weight * digit
        check_digit = (10 - (checksum % 10)) % 10
        return check_digit == digits[-1]


class AccessGudidAdapter(HttpAdapter[JSONMapping]):
    """Adapter for AccessGUDID device registry."""

    source = "accessgudid"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[JSONMapping] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap: list[JSONMapping] = list(bootstrap_records or [])

    async def fetch(self, udi_di: str) -> AsyncIterator[JSONMapping]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json("https://accessgudid.nlm.nih.gov/devices/lookup.json", params={"udi": udi_di})
        yield ensure_json_mapping(payload, context="accessgudid response")

    def parse(self, raw: JSONMapping) -> Document:
        udi_mapping = ensure_json_mapping(raw.get("udi", {}), context="accessgudid udi")
        device_identifier_value = udi_mapping.get("deviceIdentifier") or raw.get("udi_di")
        if device_identifier_value is None:
            raise ValueError("AccessGUDID record missing device identifier")
        device_identifier = str(device_identifier_value)
        brand_value = udi_mapping.get("brandName")
        model_value = udi_mapping.get("versionOrModelNumber")
        company_value = udi_mapping.get("companyName")
        description_value = udi_mapping.get("deviceDescription")
        payload: AccessGudidDocumentPayload = {
            "udi_di": device_identifier,
            "brand": brand_value if isinstance(brand_value, str) else None,
            "model": model_value if isinstance(model_value, str) else None,
            "company": company_value if isinstance(company_value, str) else None,
            "description": description_value if isinstance(description_value, str) else None,
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=device_identifier, version="v1", content=content)
        metadata: dict[str, JSONValue] = {"udi_di": device_identifier}
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps({"udi_di": device_identifier}),
            metadata=metadata,
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        udi_di = document.metadata.get("udi_di")
        if not isinstance(udi_di, str) or not UdiValidator.validate(udi_di):
            raise ValueError("Invalid UDI-DI")


class OpenFdaUdiAdapter(OpenFdaAdapter):
    """Specialized openFDA adapter for UDI endpoint with validation."""

    source = "openfda_udi"

    def parse(self, raw: JSONMapping) -> Document:  # pragma: no cover - delegate to super then enrich
        document = super().parse(raw)
        udi_di = raw.get("udi_di")
        if isinstance(udi_di, str) and udi_di:
            document.metadata["udi_di"] = udi_di
        return document

    def validate(self, document: Document) -> None:
        udi_di = document.metadata.get("udi_di")
        if udi_di and not UdiValidator.validate(str(udi_di)):
            raise ValueError("Invalid UDI-DI in openFDA payload")
        super().validate(document)
