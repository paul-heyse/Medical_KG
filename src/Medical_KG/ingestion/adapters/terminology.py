from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator, Iterable
from typing import Any

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.adapters.http import HttpAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.utils import canonical_json, normalize_text

_MESH_ID_RE = re.compile(r"^D\d{6}")
_UMLS_CUI_RE = re.compile(r"^C\d{7}")
_LOINC_RE = re.compile(r"^\d{1,5}-\d{1,2}$")
_ICD11_RE = re.compile(r"^[A-Z0-9]{3,4}")
_SNOMED_RE = re.compile(r"^\d{6,18}$")


class MeSHAdapter(HttpAdapter):
    source = "mesh"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])
        self._cache: dict[str, Any] = {}

    async def fetch(self, descriptor_id: str) -> AsyncIterator[Any]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        if descriptor_id in self._cache:
            yield self._cache[descriptor_id]
            return
        payload = await self.fetch_json("https://id.nlm.nih.gov/mesh/lookup/descriptor", params={"resource": descriptor_id})
        self._cache[descriptor_id] = payload
        yield payload

    def parse(self, raw: Any) -> Document:
        descriptor = raw.get("descriptor", {})
        descriptor_id = descriptor.get("descriptorUI")
        name = normalize_text(descriptor.get("descriptorName", {}).get("string", ""))
        concept_list = descriptor.get("conceptList", {}).get("concept", []) or []
        primary_concept = concept_list[0] if concept_list else {}
        term_list = primary_concept.get("termList", {}).get("term", []) if isinstance(primary_concept, dict) else []
        terms = [normalize_text(term.get("string", "")) for term in term_list if isinstance(term, dict)]
        payload = {
            "descriptor_id": descriptor_id,
            "name": name,
            "terms": terms,
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=descriptor_id, version="v1", content=content)
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata={"descriptor_id": descriptor_id}, raw=payload)

    def validate(self, document: Document) -> None:
        descriptor_id = document.metadata.get("descriptor_id")
        if not isinstance(descriptor_id, str) or not _MESH_ID_RE.match(descriptor_id):
            raise ValueError("Invalid MeSH descriptor id")


class UMLSAdapter(HttpAdapter):
    source = "umls"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])
        self._cache: dict[str, Any] = {}

    async def fetch(self, cui: str) -> AsyncIterator[Any]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        if cui in self._cache:
            yield self._cache[cui]
            return
        payload = await self.fetch_json("https://uts-ws.nlm.nih.gov/rest/content/current/CUI/" + cui)
        self._cache[cui] = payload
        yield payload

    def parse(self, raw: Any) -> Document:
        result = raw.get("result", {})
        cui = result.get("ui")
        payload = {
            "cui": cui,
            "name": result.get("name"),
            "synonyms": result.get("synonyms", []),
            "definition": result.get("definition"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=cui, version="v1", content=content)
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata={"cui": cui}, raw=payload)

    def validate(self, document: Document) -> None:
        cui = document.metadata.get("cui")
        if not isinstance(cui, str) or not _UMLS_CUI_RE.match(cui):
            raise ValueError("Invalid UMLS CUI")


class LoincAdapter(HttpAdapter):
    source = "loinc"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])
        self._cache: dict[str, Any] = {}

    async def fetch(self, code: str) -> AsyncIterator[Any]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        if code in self._cache:
            yield self._cache[code]
            return
        payload = await self.fetch_json("https://fhir.loinc.org/CodeSystem/$lookup", params={"code": code})
        self._cache[code] = payload
        yield payload

    def parse(self, raw: Any) -> Document:
        code = raw.get("parameter", {}).get("code") or raw.get("code")
        payload = {
            "code": code,
            "display": raw.get("display"),
            "property": raw.get("property"),
            "system": raw.get("system"),
            "method": raw.get("method"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(code), version="v1", content=content)
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata={"code": code}, raw=payload)

    def validate(self, document: Document) -> None:
        code = document.metadata.get("code")
        if not isinstance(code, str) or not _LOINC_RE.match(code):
            raise ValueError("Invalid LOINC code")


class Icd11Adapter(HttpAdapter):
    source = "icd11"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])
        self._cache: dict[str, Any] = {}

    async def fetch(self, code: str) -> AsyncIterator[Any]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        if code in self._cache:
            yield self._cache[code]
            return
        payload = await self.fetch_json(f"https://id.who.int/icd/release/11/mms/{code}")
        self._cache[code] = payload
        yield payload

    def parse(self, raw: Any) -> Document:
        code = raw.get("code")
        payload = {
            "code": code,
            "title": raw.get("title", {}).get("@value"),
            "definition": raw.get("definition", {}).get("@value"),
            "uri": raw.get("browserUrl"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(code), version="v1", content=content)
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata={"code": code}, raw=payload)

    def validate(self, document: Document) -> None:
        code = document.metadata.get("code")
        if not isinstance(code, str) or not _ICD11_RE.match(code):
            raise ValueError("Invalid ICD-11 code")


class SnomedAdapter(HttpAdapter):
    source = "snomed"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])
        self._cache: dict[str, Any] = {}

    async def fetch(self, code: str) -> AsyncIterator[Any]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        if code in self._cache:
            yield self._cache[code]
            return
        payload = await self.fetch_json("https://snowstorm.snomedserver.org/fhir/CodeSystem/$lookup", params={"code": code})
        self._cache[code] = payload
        yield payload

    def parse(self, raw: Any) -> Document:
        code = raw.get("code") or raw.get("parameter", {}).get("code")
        display = raw.get("display")
        payload = {
            "code": code,
            "display": display,
            "designation": raw.get("designation", []),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(code), version="v1", content=content)
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata={"code": code}, raw=payload)

    def validate(self, document: Document) -> None:
        code = document.metadata.get("code")
        if not isinstance(code, str) or not _SNOMED_RE.match(code):
            raise ValueError("Invalid SNOMED CT code")
        if not document.raw.get("designation"):
            raise ValueError("SNOMED record missing designation list")
