from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator, Iterable, Sequence
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
    is_snomed_payload,
)
from Medical_KG.ingestion.utils import (
    canonical_json,
    ensure_json_mapping,
    ensure_json_sequence,
    ensure_json_value,
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
        descriptor_value = raw.get("descriptor")
        descriptor = ensure_json_mapping(descriptor_value, context="mesh descriptor")

        descriptor_id_value = descriptor.get("descriptorUI")
        if not isinstance(descriptor_id_value, str) or not descriptor_id_value:
            raise ValueError("MeSH descriptor missing descriptorUI")
        descriptor_id = descriptor_id_value

        descriptor_name_value = descriptor.get("descriptorName")
        name = ""
        if isinstance(descriptor_name_value, Mapping):
            descriptor_name = ensure_json_mapping(descriptor_name_value, context="mesh descriptor name")
            name_value = descriptor_name.get("string")
            if isinstance(name_value, str):
                name = normalize_text(name_value)

        concept_list_value = descriptor.get("conceptList")
        terms: list[str] = []
        if isinstance(concept_list_value, Mapping):
            concept_list = ensure_json_mapping(concept_list_value, context="mesh concept list")
            concepts_value = concept_list.get("concept")
            if concepts_value is not None:
                for concept in ensure_json_sequence(concepts_value, context="mesh concepts"):
                    concept_map = ensure_json_mapping(concept, context="mesh concept")
                    term_list_value = concept_map.get("termList")
                    if isinstance(term_list_value, Mapping):
                        term_list = ensure_json_mapping(term_list_value, context="mesh term list")
                        term_values = term_list.get("term")
                        if term_values is not None:
                            for term_value in ensure_json_sequence(term_values, context="mesh term entries"):
                                term_map = ensure_json_mapping(term_value, context="mesh term")
                                term_string = term_map.get("string")
                                if isinstance(term_string, str):
                                    terms.append(normalize_text(term_string))

        payload: MeshDocumentPayload = {
            "descriptor_id": descriptor_id,
            "name": name,
            "terms": terms,
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=descriptor_id, version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload),
            metadata={"descriptor_id": descriptor_id},
            raw=payload,
        )

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
        result = ensure_json_mapping(raw.get("result"), context="umls result")

        cui_value = result.get("ui")
        if not isinstance(cui_value, str) or not cui_value:
            raise ValueError("UMLS result missing CUI")
        cui = cui_value

        name_value = result.get("name")
        name = normalize_text(name_value) if isinstance(name_value, str) else None

        synonyms_value = result.get("synonyms", [])
        synonyms: list[str] = []
        if isinstance(synonyms_value, Sequence):
            for synonym in synonyms_value:
                if isinstance(synonym, str):
                    synonyms.append(normalize_text(synonym))

        definition_value = result.get("definition")
        definition = normalize_text(definition_value) if isinstance(definition_value, str) else None

        payload: UmlsDocumentPayload = {
            "cui": cui,
            "name": name,
            "synonyms": synonyms,
            "definition": definition,
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=cui, version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload),
            metadata={"cui": cui},
            raw=payload,
        )

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
        parameter_value = raw.get("parameter")
        parameter = (
            ensure_json_mapping(parameter_value, context="loinc parameter")
            if isinstance(parameter_value, Mapping)
            else None
        )
        code_source = parameter.get("code") if parameter is not None else raw.get("code")
        if not isinstance(code_source, str) or not code_source:
            raise ValueError("LOINC payload missing code")
        code = code_source

        display_value = raw.get("display")
        property_value = raw.get("property")
        system_value = raw.get("system")
        method_value = raw.get("method")

        payload: LoincDocumentPayload = {
            "code": code,
            "display": normalize_text(display_value) if isinstance(display_value, str) else None,
            "property": ensure_json_value(property_value, context="loinc property"),
            "system": ensure_json_value(system_value, context="loinc system"),
            "method": ensure_json_value(method_value, context="loinc method"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=code, version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload),
            metadata={"code": code},
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
        if not isinstance(code_value, str) or not code_value:
            raise ValueError("ICD-11 payload missing code")
        code = code_value

        title_value = raw.get("title")
        title = None
        if isinstance(title_value, Mapping):
            title_map = ensure_json_mapping(title_value, context="icd11 title")
            title_raw = title_map.get("@value")
            if isinstance(title_raw, str):
                title = normalize_text(title_raw)

        definition_value = raw.get("definition")
        definition = None
        if isinstance(definition_value, Mapping):
            definition_map = ensure_json_mapping(definition_value, context="icd11 definition")
            definition_raw = definition_map.get("@value")
            if isinstance(definition_raw, str):
                definition = normalize_text(definition_raw)

        uri_value = raw.get("browserUrl")
        uri = uri_value if isinstance(uri_value, str) else None

        payload: Icd11DocumentPayload = {
            "code": code,
            "title": title,
            "definition": definition,
            "uri": uri,
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=code, version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload),
            metadata={"code": code},
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
        parameter_value = raw.get("parameter")
        parameter = (
            ensure_json_mapping(parameter_value, context="snomed parameter")
            if isinstance(parameter_value, Mapping)
            else None
        )
        code_source = raw.get("code")
        if not isinstance(code_source, str) or not code_source:
            code_candidate = parameter.get("code") if parameter is not None else None
            if not isinstance(code_candidate, str) or not code_candidate:
                raise ValueError("SNOMED payload missing code")
            code = code_candidate
        else:
            code = code_source

        display_value = raw.get("display")
        designation_value = raw.get("designation")
        designation_entries: list[JSONMapping] = []
        if designation_value is not None:
            for entry in ensure_json_sequence(designation_value, context="snomed designation"):
                designation_entries.append(ensure_json_mapping(entry, context="snomed designation entry"))

        payload: SnomedDocumentPayload = {
            "code": code,
            "display": normalize_text(display_value) if isinstance(display_value, str) else None,
            "designation": designation_entries,
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=code, version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload),
            metadata={"code": code},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        code = document.metadata.get("code")
        if not isinstance(code, str) or not _SNOMED_RE.match(code):
            raise ValueError("Invalid SNOMED CT code")
        raw_payload = document.raw
        if not is_snomed_payload(raw_payload) or not raw_payload["designation"]:
            raise ValueError("SNOMED record missing designation list")
