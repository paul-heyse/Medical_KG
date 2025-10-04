"""Terminology ingestion adapters backed by typed payload contracts.

Each adapter converts raw HTTP payloads into the TypedDict structures defined in
``Medical_KG.ingestion.types`` so that ``Document.raw`` benefits from static type
checking.  The adapters still accept ``Any`` from ``fetch`` but immediately
coerce payloads through ``ensure_json_mapping`` or ``ensure_json_sequence``
before constructing the typed payload that mypy can validate.  When a JSON value
already satisfies the schema we rely on ``narrow_to_mapping`` or
``narrow_to_sequence`` to avoid ad-hoc casts.  See ``Medical_KG.ingestion.types``
for the TypedDict definitions referenced in the inline comments below.

Optional fields:

* MeSH and UMLS payloads often include identifiers but definitions can vanish,
  so the adapters normalise blank strings to ``None`` before emitting metadata.
* LOINC entries typically provide ``display`` text while the top-level ``code``
  key may be missing from subset queries.
* ICD-11 and SNOMED data frequently omit descriptive text (``title``/``display``)
  when upstream APIs stream code-only lookups; tests ensure both presence and
  absence paths produce stable documents.
"""

from __future__ import annotations

import json
import re
from collections.abc import AsyncIterator, Iterable
from typing import Any, Mapping, Sequence

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.adapters.http import HttpAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.types import (
    Icd11DocumentPayload,
    JSONMapping,
    LoincDocumentPayload,
    MeshDocumentPayload,
    SnomedDocumentPayload,
    UmlsDocumentPayload,
    is_snomed_payload,
)
from Medical_KG.ingestion.telemetry import HttpTelemetry
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


class MeSHAdapter(HttpAdapter[Any]):
    source = "mesh"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
        telemetry: (
            HttpTelemetry
            | Sequence[HttpTelemetry]
            | Mapping[str, HttpTelemetry | Sequence[HttpTelemetry]]
        )
        | None = None,
    ) -> None:
        super().__init__(context, client, telemetry=telemetry)
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

    def parse(self, raw: Any) -> Document:
        record = ensure_json_mapping(raw, context="mesh descriptor record")
        descriptor = ensure_json_mapping(
            record.get("descriptor", {}),
            context="mesh descriptor payload",
        )
        descriptor_id_value = descriptor.get("descriptorUI")
        descriptor_id = (
            str(descriptor_id_value)
            if isinstance(descriptor_id_value, (str, int)) and str(descriptor_id_value)
            else None
        )
        name_data = descriptor.get("descriptorName")
        if isinstance(name_data, Mapping):
            raw_name = name_data.get("string", "")
        else:
            raw_name = ""
        name = normalize_text(str(raw_name))
        concept_container = ensure_json_mapping(
            descriptor.get("conceptList", {}),
            context="mesh concept list",
        )
        concept_list = ensure_json_sequence(
            concept_container.get("concept", []),
            context="mesh concept sequence",
        )
        primary_concept = concept_list[0] if concept_list else {}
        term_list: list[str] = []
        if isinstance(primary_concept, Mapping):
            term_container = ensure_json_mapping(
                primary_concept.get("termList", {}),
                context="mesh term list",
            )
            term_sequence = ensure_json_sequence(
                term_container.get("term", []),
                context="mesh term sequence",
            )
            extracted_terms: list[str] = []
            for term in term_sequence:
                if not isinstance(term, Mapping):
                    continue
                term_value = term.get("string", "")
                extracted_terms.append(normalize_text(str(term_value)))
            term_list = extracted_terms
        terms = term_list
        # ``MeshDocumentPayload.descriptor_id`` is optional, so ``None`` tracks
        # descriptors that omit a UI in the upstream payload.
        payload: MeshDocumentPayload = {
            "descriptor_id": descriptor_id,
            "name": name,
            "terms": terms,
        }
        content = canonical_json(payload)
        identifier = descriptor_id or "unknown"
        doc_id = self.build_doc_id(identifier=identifier, version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload),
            metadata={"descriptor_id": identifier},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        descriptor_id = document.metadata.get("descriptor_id")
        if not isinstance(descriptor_id, str) or not _MESH_ID_RE.match(descriptor_id):
            raise ValueError("Invalid MeSH descriptor id")


class UMLSAdapter(HttpAdapter[Any]):
    source = "umls"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
        telemetry: (
            HttpTelemetry
            | Sequence[HttpTelemetry]
            | Mapping[str, HttpTelemetry | Sequence[HttpTelemetry]]
        )
        | None = None,
    ) -> None:
        super().__init__(context, client, telemetry=telemetry)
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
        payload = await self.fetch_json(
            "https://uts-ws.nlm.nih.gov/rest/content/current/CUI/" + cui
        )
        payload_map = ensure_json_mapping(payload, context="umls response")
        self._cache[cui] = payload_map
        yield payload_map

    def parse(self, raw: Any) -> Document:
        payload_map = ensure_json_mapping(raw, context="umls record")
        result = ensure_json_mapping(payload_map.get("result", {}), context="umls result")
        cui_value = result.get("ui")
        cui = str(cui_value) if isinstance(cui_value, (str, int)) else None
        synonyms_value = ensure_json_sequence(
            result.get("synonyms", []),
            context="umls synonyms",
        )
        synonyms = [normalize_text(str(value)) for value in synonyms_value]
        name_value = result.get("name")
        name = str(name_value) if isinstance(name_value, str) else None
        definition_value = result.get("definition")
        definition = str(definition_value) if isinstance(definition_value, str) else None
        # ``UmlsDocumentPayload`` allows ``None`` for optional attributes that the
        # upstream record might omit (see ``Medical_KG.ingestion.types``).
        payload: UmlsDocumentPayload = {
            "cui": cui,
            "name": name,
            "synonyms": synonyms,
            "definition": definition,
        }
        content = canonical_json(payload)
        identifier = cui or "unknown"
        doc_id = self.build_doc_id(identifier=identifier, version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload),
            metadata={"cui": identifier},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        cui = document.metadata.get("cui")
        if not isinstance(cui, str) or not _UMLS_CUI_RE.match(cui):
            raise ValueError("Invalid UMLS CUI")


class LoincAdapter(HttpAdapter[Any]):
    source = "loinc"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
        telemetry: (
            HttpTelemetry
            | Sequence[HttpTelemetry]
            | Mapping[str, HttpTelemetry | Sequence[HttpTelemetry]]
        )
        | None = None,
    ) -> None:
        super().__init__(context, client, telemetry=telemetry)
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
            "https://fhir.loinc.org/CodeSystem/$lookup", params={"code": code}
        )
        payload_map = ensure_json_mapping(payload, context="loinc response")
        self._cache[code] = payload_map
        yield payload_map

    def parse(self, raw: Any) -> Document:
        payload_map = ensure_json_mapping(raw, context="loinc record")
        parameter = ensure_json_mapping(payload_map.get("parameter", {}), context="loinc parameter")
        code_value = parameter.get("code") or payload_map.get("code")
        if code_value is None:
            raise ValueError("LOINC payload missing code")
        code = str(code_value)
        display_value = payload_map.get("display")
        # ``LoincDocumentPayload.display`` is optional; retain ``None`` when the
        # lookup response omits a display string.
        payload: LoincDocumentPayload = {
            "code": code or None,
            "display": display_value if isinstance(display_value, str) else None,
            "property": payload_map.get("property"),
            "system": payload_map.get("system"),
            "method": payload_map.get("method"),
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


class Icd11Adapter(HttpAdapter[Any]):
    source = "icd11"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
        telemetry: (
            HttpTelemetry
            | Sequence[HttpTelemetry]
            | Mapping[str, HttpTelemetry | Sequence[HttpTelemetry]]
        )
        | None = None,
    ) -> None:
        super().__init__(context, client, telemetry=telemetry)
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

    def parse(self, raw: Any) -> Document:
        payload_map = ensure_json_mapping(raw, context="icd11 record")
        code_value = payload_map.get("code")
        code = str(code_value) if isinstance(code_value, str) and code_value else None

        title: str | None = None
        title_value = payload_map.get("title")
        if isinstance(title_value, Mapping):
            title_map = ensure_json_mapping(title_value, context="icd11 title")
            title_raw = title_map.get("@value")
            if isinstance(title_raw, str):
                title = normalize_text(title_raw)

        definition: str | None = None
        definition_value = payload_map.get("definition")
        if isinstance(definition_value, Mapping):
            definition_map = ensure_json_mapping(definition_value, context="icd11 definition")
            definition_raw = definition_map.get("@value")
            if isinstance(definition_raw, str):
                definition = normalize_text(definition_raw)

        uri_value = payload_map.get("browserUrl")
        uri = str(uri_value) if isinstance(uri_value, str) and uri_value else None
        # ``Icd11DocumentPayload`` fields map directly to the optional ``code``,
        # ``title``, ``definition`` and ``uri`` entries documented in
        # ``Medical_KG.ingestion.types``.
        payload: Icd11DocumentPayload = {
            "code": code,
            "title": title,
            "definition": definition,
            "uri": uri,
        }
        content = canonical_json(payload)
        identifier = code or uri or "unknown"
        doc_id = self.build_doc_id(identifier=identifier, version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload),
            metadata={"code": code or identifier},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        code = document.metadata.get("code")
        if not isinstance(code, str) or not _ICD11_RE.match(code):
            raise ValueError("Invalid ICD-11 code")


class SnomedAdapter(HttpAdapter[Any]):
    source = "snomed"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
        telemetry: (
            HttpTelemetry
            | Sequence[HttpTelemetry]
            | Mapping[str, HttpTelemetry | Sequence[HttpTelemetry]]
        )
        | None = None,
    ) -> None:
        super().__init__(context, client, telemetry=telemetry)
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

    def parse(self, raw: Any) -> Document:
        payload_map = ensure_json_mapping(raw, context="snomed record")
        parameter = (
            ensure_json_mapping(payload_map.get("parameter", {}), context="snomed parameter")
            if isinstance(payload_map.get("parameter"), Mapping)
            else {}
        )
        code_value = payload_map.get("code") or parameter.get("code")
        if code_value is None:
            raise ValueError("SNOMED payload missing code")
        code = str(code_value)
        display_value = payload_map.get("display")
        designation_value = ensure_json_sequence(
            payload_map.get("designation", []),
            context="snomed designation",
        )
        designation_entries = [
            ensure_json_mapping(entry, context="snomed designation entry")
            for entry in designation_value
        ]
        # ``SnomedDocumentPayload.display`` is optional; designation entries are
        # required and stay typed via ``ensure_json_mapping`` above.
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
        if is_snomed_payload(raw_payload):
            payload = raw_payload
        else:
            raise ValueError("SNOMED record missing designation list")
        if not payload.get("designation"):
            raise ValueError("SNOMED record missing designation list")
