from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator, Iterable
from typing import Any, Mapping
from typing import MutableMapping

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.adapters.http import HttpAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.utils import canonical_json, normalize_text

_CT_NCT_RE = re.compile(r"^NCT\d{8}$")
_GTIN14_RE = re.compile(r"^\d{14}$")


class ClinicalTrialsGovAdapter(HttpAdapter):
    """Adapter for ClinicalTrials.gov v2 API."""

    source = "clinicaltrials"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        api_base: str = "https://clinicaltrials.gov/api/v2",
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self.api_base = api_base.rstrip("/")
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, *_, **__) -> AsyncIterator[Any]:  # pragma: no cover - wrapper around bootstrap
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        # Minimal API loop for live use
        page_token: str | None = None
        params: dict[str, Any] = {"pageSize": 100}
        while True:
            if page_token:
                params["pageToken"] = page_token
            payload = await self.fetch_json(f"{self.api_base}/studies", params=params)
            for study in payload.get("studies", []):
                yield study
            page_token = payload.get("nextPageToken")
            if not page_token:
                break

    def parse(self, raw: Any) -> Document:
        protocol = raw.get("protocolSection", {})
        identification = protocol.get("identificationModule", {})
        nct_id = identification.get("nctId", "")
        title = normalize_text(identification.get("briefTitle", ""))
        status = protocol.get("statusModule", {}).get("overallStatus")
        summary = normalize_text(protocol.get("descriptionModule", {}).get("briefSummary", ""))
        version = raw.get("derivedSection", {}).get("miscInfoModule", {}).get("version", "unknown")
        sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
        lead_sponsor = sponsor_module.get("leadSponsor", {}) if isinstance(sponsor_module, Mapping) else {}
        enrollment_module = protocol.get("designModule", {}).get("enrollmentInfo", {})
        date_module = protocol.get("statusModule", {}) if isinstance(protocol.get("statusModule", {}), Mapping) else {}
        start_date_struct = date_module.get("startDateStruct", {}) if isinstance(date_module, Mapping) else {}
        completion_date_struct = date_module.get("completionDateStruct", {}) if isinstance(date_module, Mapping) else {}
        payload = {
            "nct_id": nct_id,
            "title": title,
            "status": status,
            "phase": ", ".join(protocol.get("designModule", {}).get("phases", []) or []),
            "study_type": protocol.get("designModule", {}).get("studyType"),
            "arms": protocol.get("armsInterventionsModule", {}).get("arms", []),
            "eligibility": protocol.get("eligibilityModule", {}).get("eligibilityCriteria"),
            "outcomes": protocol.get("outcomesModule", {}).get("primaryOutcomes", []),
            "version": version,
            "lead_sponsor": lead_sponsor.get("name") if isinstance(lead_sponsor, Mapping) else None,
            "enrollment": enrollment_module.get("count") if isinstance(enrollment_module, Mapping) else None,
            "start_date": start_date_struct.get("date"),
            "completion_date": completion_date_struct.get("date"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=nct_id, version=version, content=content)
        metadata = {
            "title": title,
            "status": status,
            "record_version": version,
        }
        if payload.get("lead_sponsor"):
            metadata["sponsor"] = payload["lead_sponsor"]
        if payload.get("phase"):
            metadata["phase"] = payload["phase"]
        if payload.get("enrollment") is not None:
            metadata["enrollment"] = payload["enrollment"]
        if payload.get("start_date"):
            metadata["start_date"] = payload["start_date"]
        if payload.get("completion_date"):
            metadata["completion_date"] = payload["completion_date"]
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
        if outcomes and not isinstance(outcomes, list):
            raise ValueError("Outcomes must be a list")


class OpenFdaAdapter(HttpAdapter):
    """Adapter for openFDA resources."""

    source = "openfda"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        api_key: str | None = None,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self.api_key = api_key
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, resource: str, *, search: str | None = None, limit: int = 100) -> AsyncIterator[Any]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        params: dict[str, Any] = {"limit": limit}
        if search:
            params["search"] = search
        if self.api_key:
            params["api_key"] = self.api_key
        payload = await self.fetch_json(f"https://api.fda.gov/{resource}.json", params=params)
        for record in payload.get("results", []):
            yield record

    def parse(self, raw: Any) -> Document:
        identifier = raw.get("safetyreportid") or raw.get("udi_di") or raw.get("setid") or raw.get("id")
        if not identifier:
            raise ValueError("Record missing identifier")
        payload = dict(raw)
        content = canonical_json(payload)
        version = raw.get("receivedate") or raw.get("version_number") or raw.get("last_updated", "unknown")
        doc_id = self.build_doc_id(identifier=str(identifier), version=str(version), content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps({"identifier": identifier}),
            metadata={"identifier": identifier},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        identifier = document.metadata.get("identifier")
        if not identifier:
            raise ValueError("openFDA document missing identifier metadata")


class DailyMedAdapter(HttpAdapter):
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

    async def fetch(self, setid: str) -> AsyncIterator[Any]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        params = {"type": "spl", "setid": setid}
        xml = await self.fetch_text("https://dailymed.nlm.nih.gov/dailymed/services/v2/spls", params=params)
        yield xml

    def parse(self, raw: Any) -> Document:
        root = ET.fromstring(raw)
        setid = root.find("setid").attrib.get("root") if root.find("setid") is not None else "unknown"
        title = normalize_text(root.findtext("title", default=""))
        sections: list[dict[str, Any]] = []
        for section in root.findall("section"):
            code_elem = section.find("code")
            loinc = code_elem.attrib.get("code") if code_elem is not None else None
            text = normalize_text(section.findtext("text", default=""))
            sections.append({"loinc": loinc, "text": text})
        payload = {"setid": setid, "title": title, "sections": sections}
        content = canonical_json(payload)
        effective = root.find("effectiveTime")
        version = effective.attrib.get("value") if effective is not None else "unknown"
        doc_id = self.build_doc_id(identifier=setid, version=version, content=content)
        return Document(doc_id=doc_id, source=self.source, content=title, metadata={"setid": setid}, raw=payload)

    def validate(self, document: Document) -> None:
        setid = document.metadata.get("setid")
        if not setid:
            raise ValueError("DailyMed record missing setid")


class RxNormAdapter(HttpAdapter):
    """Adapter for RxNav / RxNorm lookups."""

    source = "rxnorm"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, rxcui: str) -> AsyncIterator[Any]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json(f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}/properties.json")
        yield payload

    def parse(self, raw: Any) -> Document:
        props = raw.get("properties", {})
        rxcui = props.get("rxcui")
        payload = {
            "rxcui": rxcui,
            "name": props.get("name"),
            "synonym": props.get("synonym"),
            "tty": props.get("tty"),
            "ndc": props.get("ndc"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(rxcui), version="v1", content=content)
        return Document(doc_id=doc_id, source=self.source, content=props.get("name", ""), metadata={"rxcui": rxcui}, raw=payload)

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


class AccessGudidAdapter(HttpAdapter):
    """Adapter for AccessGUDID device registry."""

    source = "accessgudid"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, udi_di: str) -> AsyncIterator[Any]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json("https://accessgudid.nlm.nih.gov/devices/lookup.json", params={"udi": udi_di})
        yield payload

    def parse(self, raw: Any) -> Document:
        udi = raw.get("udi", {})
        device_identifier = udi.get("deviceIdentifier") or raw.get("udi_di")
        payload = {
            "udi_di": device_identifier,
            "brand": udi.get("brandName"),
            "model": udi.get("versionOrModelNumber"),
            "company": udi.get("companyName"),
            "description": udi.get("deviceDescription"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(device_identifier), version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps({"udi_di": device_identifier}),
            metadata={"udi_di": device_identifier},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        udi_di = document.metadata.get("udi_di")
        if not isinstance(udi_di, str) or not UdiValidator.validate(udi_di):
            raise ValueError("Invalid UDI-DI")


class OpenFdaUdiAdapter(OpenFdaAdapter):
    """Specialized openFDA adapter for UDI endpoint with validation."""

    source = "openfda_udi"

    def parse(self, raw: Any) -> Document:  # pragma: no cover - delegate to super then enrich
        document = super().parse(raw)
        udi_di = raw.get("udi_di")
        if udi_di:
            if isinstance(document.metadata, MutableMapping):
                document.metadata["udi_di"] = udi_di
        return document

    def validate(self, document: Document) -> None:
        udi_di = document.metadata.get("udi_di")
        if udi_di and not UdiValidator.validate(str(udi_di)):
            raise ValueError("Invalid UDI-DI in openFDA payload")
        super().validate(document)
