from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator, Iterable
from typing import Any

from dataclasses import replace

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.adapters.http import HttpAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.models import Document, IngestionResult
from Medical_KG.ingestion.utils import canonical_json, normalize_text

_MESH_ID_RE = re.compile(r"^D\d{6}")
_UMLS_CUI_RE = re.compile(r"^C\d{7}")
_LOINC_RE = re.compile(r"^\d{1,5}-\d{1,2}$")
_ICD11_RE = re.compile(r"^[A-Z0-9]{3,4}")
_SNOMED_RE = re.compile(r"^\d{6,18}$")


class _CachedTerminologyAdapter(HttpAdapter):
    """Cache terminology lookups within a single adapter instance."""

    cache_key: str

    def __init__(self, context: AdapterContext, client: AsyncHttpClient) -> None:
        super().__init__(context, client)
        self._cache: dict[str, tuple[IngestionResult, ...]] = {}

    def _extract_cache_key(self, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
        if self.cache_key in kwargs:
            value = kwargs[self.cache_key]
        elif args:
            value = args[0]
        else:  # pragma: no cover - defensive, enforced by tests
            raise ValueError(f"Missing cache key '{self.cache_key}'")
        if not isinstance(value, str):  # pragma: no cover - defensive guard
            raise ValueError(f"Cache key '{self.cache_key}' must be a string")
        return value

    async def run(self, *args: Any, **kwargs: Any) -> Iterable[IngestionResult]:
        key = self._extract_cache_key(args, kwargs)
        if key in self._cache:
            return [replace(result) for result in self._cache[key]]
        results = await super().run(*args, **kwargs)
        if results:
            self._cache[key] = tuple(replace(result) for result in results)
        return results


class MeSHAdapter(_CachedTerminologyAdapter):
    source = "mesh"
    cache_key = "descriptor_id"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, descriptor_id: str) -> AsyncIterator[Any]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json("https://id.nlm.nih.gov/mesh/lookup/descriptor", params={"resource": descriptor_id})
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


class UMLSAdapter(_CachedTerminologyAdapter):
    source = "umls"
    cache_key = "cui"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, cui: str) -> AsyncIterator[Any]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json("https://uts-ws.nlm.nih.gov/rest/content/current/CUI/" + cui)
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


class LoincAdapter(_CachedTerminologyAdapter):
    source = "loinc"
    cache_key = "code"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, code: str) -> AsyncIterator[Any]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json("https://fhir.loinc.org/CodeSystem/$lookup", params={"code": code})
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


class Icd11Adapter(_CachedTerminologyAdapter):
    source = "icd11"
    cache_key = "code"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, code: str) -> AsyncIterator[Any]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json(f"https://id.who.int/icd/release/11/mms/{code}")
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


class SnomedAdapter(_CachedTerminologyAdapter):
    source = "snomed"
    cache_key = "code"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(self, code: str) -> AsyncIterator[Any]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        payload = await self.fetch_json("https://snowstorm.snomedserver.org/fhir/CodeSystem/$lookup", params={"code": code})
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
