from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator, Iterable, Sequence
from typing import Mapping, cast

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.adapters.http import HttpAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.payloads import (
    AccessGudidDocumentPayload,
    AccessGudidPayload,
    ClinicalStudyDocumentPayload,
    ClinicalStudyPayload,
    ClinicalStudiesResponse,
    DailyMedDocumentPayload,
    DailyMedSection,
    OpenFdaPayload,
    RxNormDocumentPayload,
    RxNormPayload,
)
from Medical_KG.ingestion.utils import canonical_json, normalize_text

_CT_NCT_RE = re.compile(r"^NCT\d{8}$")
_GTIN14_RE = re.compile(r"^\d{14}$")


class ClinicalTrialsGovAdapter(HttpAdapter[ClinicalStudyPayload]):
    """Adapter for ClinicalTrials.gov v2 API."""

    source = "clinicaltrials"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        api_base: str = "https://clinicaltrials.gov/api/v2",
        bootstrap_records: Iterable[ClinicalStudyPayload] | None = None,
    ) -> None:
        super().__init__(context, client)
        self.api_base = api_base.rstrip("/")
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, *_: object, **__: object) -> AsyncIterator[ClinicalStudyPayload]:  # pragma: no cover - wrapper around bootstrap
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        page_token: str | None = None
        params: dict[str, object] = {"pageSize": 100}
        while True:
            if page_token:
                params["pageToken"] = page_token
            payload = await self.fetch_json(f"{self.api_base}/studies", params=params)
            data = cast(ClinicalStudiesResponse, payload if isinstance(payload, Mapping) else {})
            for study in data.get("studies", []):
                yield study
            page_token = data.get("nextPageToken")
            if not page_token:
                break

    def parse(self, raw: ClinicalStudyPayload) -> Document:
        protocol = cast(Mapping[str, object], raw.get("protocolSection") or {})
        identification = cast(Mapping[str, object], protocol.get("identificationModule") or {})
        status_module = cast(Mapping[str, object], protocol.get("statusModule") or {})
        description_module = cast(Mapping[str, object], protocol.get("descriptionModule") or {})
        design_module = cast(Mapping[str, object], protocol.get("designModule") or {})
        arms_module = cast(Mapping[str, object], protocol.get("armsInterventionsModule") or {})
        eligibility_module = cast(Mapping[str, object], protocol.get("eligibilityModule") or {})
        outcomes_module = cast(Mapping[str, object], protocol.get("outcomesModule") or {})
        derived = cast(Mapping[str, object], raw.get("derivedSection") or {})
        misc_info = cast(Mapping[str, object], derived.get("miscInfoModule") or {})

        nct_id = str(identification.get("nctId") or "")
        title = normalize_text(str(identification.get("briefTitle") or ""))
        status = status_module.get("overallStatus")
        summary = normalize_text(str(description_module.get("briefSummary") or ""))
        phases = cast(Sequence[str], design_module.get("phases") or [])
        study_type = design_module.get("studyType")
        arms = cast(Sequence[Mapping[str, object]], arms_module.get("arms") or [])
        eligibility = eligibility_module.get("eligibilityCriteria")
        outcomes = cast(Sequence[Mapping[str, object]], outcomes_module.get("primaryOutcomes") or [])
        version = str(misc_info.get("version") or "unknown")

        payload: ClinicalStudyDocumentPayload = {
            "nct_id": nct_id,
            "title": title,
            "status": cast(str | None, status),
            "phase": ", ".join(phases) if phases else "",
            "study_type": cast(str | None, study_type),
            "arms": arms,
            "eligibility": cast(str | None, eligibility),
            "outcomes": outcomes,
            "version": version,
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=nct_id, version=version, content=content)
        metadata: dict[str, object] = {
            "title": title,
            "status": status,
            "record_version": version,
        }
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=summary or title,
            metadata=metadata,
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        raw = document.raw if isinstance(document.raw, Mapping) else {}
        nct_id = raw.get("nct_id")
        if not isinstance(nct_id, str) or not _CT_NCT_RE.match(nct_id):
            raise ValueError(f"Invalid NCT ID: {nct_id}")
        outcomes = raw.get("outcomes", [])
        if outcomes and not isinstance(outcomes, Sequence):
            raise ValueError("Outcomes must be a sequence")


class OpenFdaAdapter(HttpAdapter[OpenFdaPayload]):
    """Adapter for openFDA resources."""

    source = "openfda"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        api_key: str | None = None,
        bootstrap_records: Iterable[OpenFdaPayload] | None = None,
    ) -> None:
        super().__init__(context, client)
        self.api_key = api_key
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(
        self,
        resource: str,
        *,
        search: str | None = None,
        limit: int = 100,
    ) -> AsyncIterator[OpenFdaPayload]:
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
        data = cast(Mapping[str, object], payload if isinstance(payload, Mapping) else {})
        results = cast(Sequence[OpenFdaPayload], data.get("results") or [])
        for record in results:
            yield record

    def parse(self, raw: OpenFdaPayload) -> Document:
        identifier = raw.get("safetyreportid") or raw.get("udi_di") or raw.get("setid") or raw.get("id")
        if not identifier:
            raise ValueError("Record missing identifier")
        payload: dict[str, object] = dict(raw)
        payload.setdefault("identifier", str(identifier))
        content = canonical_json(payload)
        version = (
            raw.get("receivedate")
            or raw.get("version_number")
            or raw.get("last_updated")
            or "unknown"
        )
        doc_id = self.build_doc_id(identifier=str(identifier), version=str(version), content=content)
        metadata: dict[str, object] = {"identifier": str(identifier)}
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps({"identifier": identifier}),
            metadata=metadata,
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        identifier = document.metadata.get("identifier")
        if not identifier:
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
        params: Mapping[str, object] = {"type": "spl", "setid": setid}
        xml = await self.fetch_text("https://dailymed.nlm.nih.gov/dailymed/services/v2/spls", params=params)
        yield xml

    def parse(self, raw: str) -> Document:
        root = ET.fromstring(raw)
        setid = root.findtext("setid") or "unknown"
        title = normalize_text(root.findtext("title", default=""))
        sections: list[DailyMedSection] = []
        for section in root.findall("section"):
            code_elem = section.find("code")
            loinc = code_elem.attrib.get("code") if code_elem is not None else None
            text = normalize_text(section.findtext("text", default=""))
            sections.append({"loinc": loinc, "text": text})
        payload: DailyMedDocumentPayload = {"setid": setid, "title": title, "sections": sections}
        content = canonical_json(payload)
        effective = root.find("effectiveTime")
        version = effective.attrib.get("value") if effective is not None else "unknown"
        doc_id = self.build_doc_id(identifier=setid, version=version, content=content)
        metadata: dict[str, object] = {"setid": setid}
        return Document(doc_id=doc_id, source=self.source, content=title, metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        setid = document.metadata.get("setid")
        if not setid:
            raise ValueError("DailyMed record missing setid")


class RxNormAdapter(HttpAdapter[RxNormPayload]):
    """Adapter for RxNav / RxNorm lookups."""

    source = "rxnorm"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[RxNormPayload] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, rxcui: str) -> AsyncIterator[RxNormPayload]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json(f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/properties.json")
        data = cast(RxNormPayload, payload if isinstance(payload, Mapping) else {})
        yield data

    def parse(self, raw: RxNormPayload) -> Document:
        props = cast(Mapping[str, object], raw.get("properties") or {})
        rxcui = props.get("rxcui")
        name = cast(str | None, props.get("name"))
        payload: RxNormDocumentPayload = {
            "rxcui": str(rxcui) if rxcui is not None else "",
            "name": name,
            "synonym": cast(str | None, props.get("synonym")),
            "tty": cast(str | None, props.get("tty")),
            "ndc": cast(str | None, props.get("ndc")),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(rxcui), version="v1", content=content)
        metadata: dict[str, object] = {"rxcui": rxcui}
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=name or "",
            metadata=metadata,
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


class AccessGudidAdapter(HttpAdapter[AccessGudidPayload]):
    """Adapter for AccessGUDID device registry."""

    source = "accessgudid"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[AccessGudidPayload] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, udi_di: str) -> AsyncIterator[AccessGudidPayload]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json(
            "https://accessgudid.nlm.nih.gov/devices/lookup.json",
            params={"udi": udi_di},
        )
        data = cast(AccessGudidPayload, payload if isinstance(payload, Mapping) else {})
        yield data

    def parse(self, raw: AccessGudidPayload) -> Document:
        udi = cast(Mapping[str, object], raw.get("udi") or {})
        device_identifier = udi.get("deviceIdentifier") or raw.get("udi_di")
        payload: AccessGudidDocumentPayload = {
            "udi_di": cast(str | None, device_identifier),
            "brand": cast(str | None, udi.get("brandName")),
            "model": cast(str | None, udi.get("versionOrModelNumber")),
            "company": cast(str | None, udi.get("companyName")),
            "description": cast(str | None, udi.get("deviceDescription")),
        }
        content = canonical_json(payload)
        identifier = str(device_identifier) if device_identifier is not None else ""
        doc_id = self.build_doc_id(identifier=identifier, version="v1", content=content)
        metadata: dict[str, object] = {"udi_di": device_identifier}
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

    def parse(self, raw: OpenFdaPayload) -> Document:  # pragma: no cover - delegate to super then enrich
        document = super().parse(raw)
        udi_di = raw.get("udi_di")
        if udi_di is not None:
            document.metadata["udi_di"] = udi_di
        return document

    def validate(self, document: Document) -> None:
        udi_di = document.metadata.get("udi_di")
        if udi_di and (not isinstance(udi_di, str) or not UdiValidator.validate(udi_di)):
            raise ValueError("Invalid UDI-DI in openFDA payload")
        super().validate(document)
