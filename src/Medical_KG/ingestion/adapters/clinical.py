"""Clinical ingestion adapters limit runtime validation to HTTP boundaries.

The fetch methods document the expected API response shapes while the parse
methods rely on the TypedDict payload contracts introduced in the typed payload
refactor. Redundant calls to ``ensure_json_*`` inside parse flows have been
removed so we only coerce external JSON at the network boundary.

Optional field guidance:

* ClinicalTrials.gov records commonly include ``status``, ``lead_sponsor`` and
  ``start_date`` metadata, while ``completion_date`` and detailed ``outcomes``
  entries are frequently absent in bootstrap fixtures.
* AccessGUDID payloads usually provide ``brand`` and ``description`` but rarely
  populate ``model`` and ``company`` fields.
* RxNorm lookups reliably supply ``name``/``tty`` values, whereas ``synonym``
  and ``ndc`` keys appear sporadically. Tests cover both the present and absent
  cases so adapters never assume their availability.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator, Iterable, Sequence as SequenceABC
from typing import Mapping, MutableMapping, Sequence

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
    normalize_text,
)

_CT_NCT_RE = re.compile(r"^NCT\d{8}$")
_GTIN14_RE = re.compile(r"^\d{14}$")


def _coerce_mapping(value: JSONValue | None) -> MutableMapping[str, JSONValue]:
    """Return a mutable mapping when the input already has mapping shape."""

    return dict(value) if isinstance(value, Mapping) else {}


def _iter_json_mappings(value: JSONValue | None) -> Iterable[JSONMapping]:
    """Yield child mappings when the upstream JSON value is a sequence."""

    if isinstance(value, SequenceABC) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            if isinstance(item, Mapping):
                yield dict(item)


def _coerce_json_value(value: object) -> JSONValue:
    """Coerce loosely typed JSON payload values without runtime validation."""

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, SequenceABC) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return str(value)


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
            payload_map = ensure_json_mapping(
                payload,
                context="clinicaltrials response",
            )
            # ClinicalTrials.gov v2 (2024-01 schema) documents a JSON object
            # envelope with a ``studies`` array.
            studies_value = payload_map.get("studies", [])
            # The v2 pagination response documents ``studies`` as an array of
            # study objects; keep boundary validation in case the API shape
            # changes.
            for study_value in ensure_json_sequence(
                studies_value,
                context="clinicaltrials studies",
            ):
                # Individual study entries remain JSON objects in the v2
                # pagination response.
                study_map = ensure_json_mapping(
                    study_value,
                    context="clinicaltrials study",
                )
                protocol_section_value = study_map.get("protocolSection")
                if not isinstance(protocol_section_value, Mapping):
                    continue
                protocol_section = dict(protocol_section_value)
                study_payload: ClinicalTrialsStudyPayload = {
                    "protocolSection": dict(protocol_section),
                }
                derived_section_value = study_map.get("derivedSection")
                if isinstance(derived_section_value, Mapping):
                    study_payload["derivedSection"] = dict(derived_section_value)
                yield study_payload
            next_token_value = payload_map.get("nextPageToken")
            page_token = next_token_value if isinstance(next_token_value, str) and next_token_value else None
            if not page_token:
                break

    def parse(self, raw: ClinicalTrialsStudyPayload) -> Document:
        protocol = _coerce_mapping(raw.get("protocolSection"))
        identification = _coerce_mapping(protocol.get("identificationModule"))
        nct_id = str(identification.get("nctId", ""))
        title_value = identification.get("briefTitle")
        title = normalize_text(title_value) if isinstance(title_value, str) else ""

        status_module = _coerce_mapping(protocol.get("statusModule"))
        status_value = status_module.get("overallStatus")
        status = str(status_value) if isinstance(status_value, str) else None

        description_module = _coerce_mapping(protocol.get("descriptionModule"))
        summary_value = description_module.get("briefSummary")
        summary = normalize_text(summary_value) if isinstance(summary_value, str) else ""

        derived_section = _coerce_mapping(raw.get("derivedSection"))
        misc_info = _coerce_mapping(derived_section.get("miscInfoModule"))
        version_value = misc_info.get("version")
        version = str(version_value) if version_value else "unknown"

        sponsor_module = _coerce_mapping(protocol.get("sponsorCollaboratorsModule"))
        lead_sponsor_mapping = _coerce_mapping(sponsor_module.get("leadSponsor"))
        lead_sponsor_name_value = lead_sponsor_mapping.get("name")
        lead_sponsor_name = lead_sponsor_name_value if isinstance(lead_sponsor_name_value, str) else None

        design_module = _coerce_mapping(protocol.get("designModule"))
        phases_value = design_module.get("phases")
        phases: list[str] = []
        if isinstance(phases_value, SequenceABC) and not isinstance(phases_value, (str, bytes, bytearray)):
            for phase in phases_value:
                if isinstance(phase, str):
                    phases.append(phase)
        phase_text = ", ".join(phases) or None
        study_type_value = design_module.get("studyType")
        study_type = study_type_value if isinstance(study_type_value, str) else None

        enrollment_info = _coerce_mapping(design_module.get("enrollmentInfo"))
        enrollment_raw = enrollment_info.get("count")
        enrollment: int | str | None
        if isinstance(enrollment_raw, int):
            enrollment = enrollment_raw
        elif isinstance(enrollment_raw, str):
            enrollment = enrollment_raw
        else:
            enrollment = None

        start_date_struct = _coerce_mapping(status_module.get("startDateStruct"))
        start_date_value = start_date_struct.get("date")
        start_date = start_date_value if isinstance(start_date_value, str) else None

        completion_date_struct = _coerce_mapping(status_module.get("completionDateStruct"))
        completion_date_value = completion_date_struct.get("date")
        completion_date = completion_date_value if isinstance(completion_date_value, str) else None

        arms_module = _coerce_mapping(protocol.get("armsInterventionsModule"))
        arms_list = list(_iter_json_mappings(arms_module.get("arms")))

        eligibility_module = _coerce_mapping(protocol.get("eligibilityModule"))
        eligibility = _coerce_json_value(eligibility_module.get("eligibilityCriteria"))

        outcomes_module = _coerce_mapping(protocol.get("outcomesModule"))
        outcomes_list = list(_iter_json_mappings(outcomes_module.get("primaryOutcomes")))
        outcomes_payload: Sequence[JSONMapping] | None = outcomes_list or None

        payload: ClinicalDocumentPayload = {
            "nct_id": nct_id,
            "title": title,
            "status": status,
            "phase": phase_text,
            "study_type": study_type,
            "arms": arms_list,
            "eligibility": eligibility,
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
        payload_map = ensure_json_mapping(
            payload,
            context="openfda response",
        )
        # openFDA device/drug APIs (v1, 2023-11 docs) return a JSON object with
        # a ``results`` array payload.
        results_value = payload_map.get("results", [])
        for record_value in ensure_json_sequence(
            results_value,
            context="openfda results",
        ):
            # Each ``results`` entry is documented as a JSON object containing a
            # device or adverse-event record.
            record_map = ensure_json_mapping(
                record_value,
                context="openfda record",
            )
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
        record_payload: dict[str, JSONValue] = dict(raw)
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
        yield ensure_json_mapping(
            payload,
            context="rxnorm response",
        )
        # RxNav v1.0 responses wrap the drug properties inside a JSON object with
        # a ``properties`` payload section.

    def parse(self, raw: JSONMapping) -> Document:
        props = _coerce_mapping(raw.get("properties"))
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
        yield ensure_json_mapping(
            payload,
            context="accessgudid response",
        )
        # AccessGUDID device lookup (2019 API guide) returns a JSON envelope with
        # an optional ``udi`` object containing device metadata.

    def parse(self, raw: JSONMapping) -> Document:
        udi_mapping = _coerce_mapping(raw.get("udi"))
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
