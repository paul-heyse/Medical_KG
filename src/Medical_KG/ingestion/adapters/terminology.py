from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator, Iterable, Sequence
from typing import Mapping, cast

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


class MeSHAdapter(HttpAdapter[Mapping[str, object]]):
    source = "mesh"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[Mapping[str, object]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, descriptor_id: str) -> AsyncIterator[Mapping[str, object]]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json("https://id.nlm.nih.gov/mesh/lookup/descriptor", params={"resource": descriptor_id})
        data = cast(Mapping[str, object], payload if isinstance(payload, Mapping) else {})
        yield data

    def parse(self, raw: Mapping[str, object]) -> Document:
        descriptor = cast(Mapping[str, object], raw.get("descriptor", {}))
        descriptor_id = descriptor.get("descriptorUI")
        name = normalize_text(cast(str, cast(Mapping[str, object], descriptor.get("descriptorName", {})).get("string", "")))
        concept_list = cast(Mapping[str, object], descriptor.get("conceptList", {})).get("concept", [])
        concepts = cast(Sequence[Mapping[str, object]], concept_list or [])
        primary_concept = concepts[0] if concepts else {}
        term_list = cast(Mapping[str, object], primary_concept.get("termList", {})).get("term", [])
        terms_raw = cast(Sequence[Mapping[str, object]], term_list if isinstance(term_list, Sequence) else [])
        terms = [normalize_text(str(term.get("string", ""))) for term in terms_raw]
        payload = {
            "descriptor_id": descriptor_id,
            "name": name,
            "terms": terms,
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(descriptor_id), version="v1", content=content)
        metadata: dict[str, object] = {"descriptor_id": descriptor_id or ""}
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        descriptor_id = document.metadata.get("descriptor_id")
        if not isinstance(descriptor_id, str) or not _MESH_ID_RE.match(descriptor_id):
            raise ValueError("Invalid MeSH descriptor id")


class UMLSAdapter(HttpAdapter[Mapping[str, object]]):
    source = "umls"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[Mapping[str, object]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, cui: str) -> AsyncIterator[Mapping[str, object]]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json("https://uts-ws.nlm.nih.gov/rest/content/current/CUI/" + cui)
        data = cast(Mapping[str, object], payload if isinstance(payload, Mapping) else {})
        yield data

    def parse(self, raw: Mapping[str, object]) -> Document:
        result = cast(Mapping[str, object], raw.get("result", {}))
        cui = result.get("ui")
        payload = {
            "cui": cui,
            "name": result.get("name"),
            "synonyms": result.get("synonyms", []),
            "definition": result.get("definition"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(cui), version="v1", content=content)
        metadata: dict[str, object] = {"cui": cui or ""}
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        cui = document.metadata.get("cui")
        if not isinstance(cui, str) or not _UMLS_CUI_RE.match(cui):
            raise ValueError("Invalid UMLS CUI")


class LoincAdapter(HttpAdapter[Mapping[str, object]]):
    source = "loinc"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[Mapping[str, object]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, code: str) -> AsyncIterator[Mapping[str, object]]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json("https://fhir.loinc.org/CodeSystem/$lookup", params={"code": code})
        data = cast(Mapping[str, object], payload if isinstance(payload, Mapping) else {})
        yield data

    def parse(self, raw: Mapping[str, object]) -> Document:
        parameter = cast(Mapping[str, object], raw.get("parameter", {}))
        code = raw.get("code") or parameter.get("code")
        payload = {
            "code": code,
            "display": raw.get("display"),
            "property": raw.get("property"),
            "system": raw.get("system"),
            "method": raw.get("method"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(code), version="v1", content=content)
        metadata: dict[str, object] = {"code": code or ""}
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        code = document.metadata.get("code")
        if not isinstance(code, str) or not _LOINC_RE.match(code):
            raise ValueError("Invalid LOINC code")


class Icd11Adapter(HttpAdapter[Mapping[str, object]]):
    source = "icd11"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[Mapping[str, object]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, code: str) -> AsyncIterator[Mapping[str, object]]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json(f"https://id.who.int/icd/release/11/mms/{code}")
        data = cast(Mapping[str, object], payload if isinstance(payload, Mapping) else {})
        yield data

    def parse(self, raw: Mapping[str, object]) -> Document:
        code = raw.get("code")
        title = cast(Mapping[str, object], raw.get("title", {})).get("@value")
        definition = cast(Mapping[str, object], raw.get("definition", {})).get("@value")
        payload = {
            "code": code,
            "title": title,
            "definition": definition,
            "uri": raw.get("browserUrl"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(code), version="v1", content=content)
        metadata: dict[str, object] = {"code": code or ""}
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        code = document.metadata.get("code")
        if not isinstance(code, str) or not _ICD11_RE.match(code):
            raise ValueError("Invalid ICD-11 code")


class SnomedAdapter(HttpAdapter[Mapping[str, object]]):
    source = "snomed"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[Mapping[str, object]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, code: str) -> AsyncIterator[Mapping[str, object]]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json("https://snowstorm.snomedserver.org/fhir/CodeSystem/$lookup", params={"code": code})
        data = cast(Mapping[str, object], payload if isinstance(payload, Mapping) else {})
        yield data

    def parse(self, raw: Mapping[str, object]) -> Document:
        code = raw.get("code") or cast(Mapping[str, object], raw.get("parameter", {})).get("code")
        display = raw.get("display")
        payload = {
            "code": code,
            "display": display,
            "designation": raw.get("designation", []),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(code), version="v1", content=content)
        metadata: dict[str, object] = {"code": code or ""}
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        code = document.metadata.get("code")
        if not isinstance(code, str) or not _SNOMED_RE.match(code):
            raise ValueError("Invalid SNOMED CT code")
        raw = document.raw if isinstance(document.raw, Mapping) else {}
        if not raw.get("designation"):
            raise ValueError("SNOMED record missing designation list")
