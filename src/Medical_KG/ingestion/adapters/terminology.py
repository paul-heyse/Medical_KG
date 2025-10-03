from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator, Iterable
from typing import Any, Mapping

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.adapters.http import HttpAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.types import (
    JSONMapping,
    Icd11DocumentPayload,
    LoincDocumentPayload,
    MeshDocumentPayload,
    SnomedDocumentPayload,
    UmlsDocumentPayload,
)
from Medical_KG.ingestion.utils import (
    canonical_json,
    ensure_json_mapping,
    ensure_json_sequence,
    normalize_text,
)

_MESH_ID_RE = re.compile(r"^D\d{6}")
_UMLS_CUI_RE = re.compile(r"^C\d{7}")
_LOINC_RE = re.compile(r"^\d{1,5}-\d{1,2}$")
_ICD11_RE = re.compile(r"^[A-Z0-9]{3,4}")
_SNOMED_RE = re.compile(r"^\d{6,18}$")


class MeSHAdapter(HttpAdapter[JSONMapping]):
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
        self._cache: dict[str, JSONMapping] = {}

    async def fetch(self, descriptor_id: str) -> AsyncIterator[JSONMapping]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        if descriptor_id in self._cache:
            yield self._cache[descriptor_id]
            return
        payload = await self.fetch_json(
            "https://id.nlm.nih.gov/mesh/lookup/descriptor",
            params={"resource": descriptor_id},
        )
        payload_map = ensure_json_mapping(payload, context="mesh descriptor response")
        self._cache[descriptor_id] = payload_map
        yield payload_map

    def parse(self, raw: JSONMapping) -> Document:
        descriptor_raw = raw.get("descriptor", {})
        descriptor = ensure_json_mapping(descriptor_raw, context="mesh descriptor payload")
        descriptor_id_value = descriptor.get("descriptorUI")
        descriptor_id = str(descriptor_id_value) if isinstance(descriptor_id_value, str) else ""
        name = normalize_text(descriptor.get("descriptorName", {}).get("string", ""))
        concept_list = descriptor.get("conceptList", {}).get("concept", []) or []
        primary_concept = concept_list[0] if concept_list else {}
        term_list = primary_concept.get("termList", {}).get("term", []) if isinstance(primary_concept, dict) else []
        terms = [normalize_text(term.get("string", "")) for term in term_list if isinstance(term, dict)]
        payload: MeshDocumentPayload = {
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


class UMLSAdapter(HttpAdapter[JSONMapping]):
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
        self._cache: dict[str, JSONMapping] = {}

    async def fetch(self, cui: str) -> AsyncIterator[JSONMapping]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        if cui in self._cache:
            yield self._cache[cui]
            return
        payload = await self.fetch_json("https://uts-ws.nlm.nih.gov/rest/content/current/CUI/" + cui)
        payload_map = ensure_json_mapping(payload, context="umls response")
        self._cache[cui] = payload_map
        yield payload_map

    def parse(self, raw: JSONMapping) -> Document:
        result = ensure_json_mapping(raw.get("result", {}), context="umls result")
        cui = result.get("ui")
        payload: UmlsDocumentPayload = {
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


class LoincAdapter(HttpAdapter[JSONMapping]):
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
        self._cache: dict[str, JSONMapping] = {}

    async def fetch(self, code: str) -> AsyncIterator[JSONMapping]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        if code in self._cache:
            yield self._cache[code]
            return
        payload = await self.fetch_json("https://fhir.loinc.org/CodeSystem/$lookup", params={"code": code})
        payload_map = ensure_json_mapping(payload, context="loinc response")
        self._cache[code] = payload_map
        yield payload_map

    def parse(self, raw: JSONMapping) -> Document:
        parameter = ensure_json_mapping(raw.get("parameter", {}), context="loinc parameter")
        code_value = parameter.get("code") or raw.get("code")
        if code_value is None:
            raise ValueError("LOINC payload missing code")
        code = str(code_value)
        payload: LoincDocumentPayload = {
            "code": code or None,
            "display": raw.get("display") if isinstance(raw.get("display"), str) else None,
            "property": raw.get("property"),
            "system": raw.get("system"),
            "method": raw.get("method"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=code, version="v1", content=content)
        metadata_value = code
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload),
            metadata={"code": metadata_value},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        code = document.metadata.get("code")
        if not isinstance(code, str) or not _LOINC_RE.match(code):
            raise ValueError("Invalid LOINC code")


class Icd11Adapter(HttpAdapter[JSONMapping]):
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
        self._cache: dict[str, JSONMapping] = {}

    async def fetch(self, code: str) -> AsyncIterator[JSONMapping]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        if code in self._cache:
            yield self._cache[code]
            return
        payload = await self.fetch_json(f"https://id.who.int/icd/release/11/mms/{code}")
        payload_map = ensure_json_mapping(payload, context="icd11 response")
        self._cache[code] = payload_map
        yield payload_map

    def parse(self, raw: JSONMapping) -> Document:
        code_value = raw.get("code")
        code = str(code_value) if isinstance(code_value, str) else None
        title_value = raw.get("title")
        title_text = None
        if isinstance(title_value, Mapping):
            title_text = ensure_json_mapping(title_value, context="icd11 title").get("@value")

        definition_value = raw.get("definition")
        definition_text = None
        if isinstance(definition_value, Mapping):
            definition_text = ensure_json_mapping(definition_value, context="icd11 definition").get("@value")

        uri_value = raw.get("browserUrl")
        payload: Icd11DocumentPayload = {
            "code": code,
            "title": title_text if isinstance(title_text, str) else None,
            "definition": definition_text if isinstance(definition_text, str) else None,
            "uri": uri_value if isinstance(uri_value, str) else None,
        }
        content = canonical_json(payload)
        identifier = code or "unknown"
        doc_id = self.build_doc_id(identifier=identifier, version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload),
            metadata={"code": identifier},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        code = document.metadata.get("code")
        if not isinstance(code, str) or not _ICD11_RE.match(code):
            raise ValueError("Invalid ICD-11 code")


class SnomedAdapter(HttpAdapter[JSONMapping]):
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
        self._cache: dict[str, JSONMapping] = {}

    async def fetch(self, code: str) -> AsyncIterator[JSONMapping]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        if code in self._cache:
            yield self._cache[code]
            return
        payload = await self.fetch_json(
            "https://snowstorm.snomedserver.org/fhir/CodeSystem/$lookup",
            params={"code": code},
        )
        payload_map = ensure_json_mapping(payload, context="snomed response")
        self._cache[code] = payload_map
        yield payload_map

    def parse(self, raw: JSONMapping) -> Document:
        parameter = ensure_json_mapping(raw.get("parameter", {}), context="snomed parameter") if isinstance(raw.get("parameter"), Mapping) else {}
        code_value = raw.get("code") or parameter.get("code")
        if code_value is None:
            raise ValueError("SNOMED payload missing code")
        code = str(code_value)
        display_value = raw.get("display")
        designation_value = ensure_json_sequence(raw.get("designation", []), context="snomed designation")
        designation_entries = [
            ensure_json_mapping(entry, context="snomed designation entry") for entry in designation_value
        ]
        payload: SnomedDocumentPayload = {
            "code": code or None,
            "display": display_value if isinstance(display_value, str) else None,
            "designation": designation_entries,
        }
        content = canonical_json(payload)
        identifier = code
        doc_id = self.build_doc_id(identifier=identifier, version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload),
            metadata={"code": identifier},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        code = document.metadata.get("code")
        if not isinstance(code, str) or not _SNOMED_RE.match(code):
            raise ValueError("Invalid SNOMED CT code")
        raw_payload = document.raw
        if not isinstance(raw_payload, dict) or not raw_payload.get("designation"):
            raise ValueError("SNOMED record missing designation list")
