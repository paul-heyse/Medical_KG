from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator, Iterable
from typing import Generic, Mapping, Sequence, TypeVar, cast

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.adapters.http import HttpAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.types import (
    CdcSocrataDocumentPayload,
    CdcWonderDocumentPayload,
    JSONMapping,
    JSONValue,
    NiceGuidelineDocumentPayload,
    OpenPrescribingDocumentPayload,
    UspstfDocumentPayload,
    WhoGhoDocumentPayload,
)
from Medical_KG.ingestion.utils import (
    canonical_json,
    ensure_json_mapping,
    ensure_json_sequence,
    normalize_text,
)


RawBootstrapT = TypeVar("RawBootstrapT")


class _BootstrapAdapter(HttpAdapter[RawBootstrapT], Generic[RawBootstrapT]):
    """Adapter base class that can iterate over bootstrap records."""

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[RawBootstrapT] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap: list[RawBootstrapT] = list(bootstrap_records or [])

    async def _yield_bootstrap(self) -> AsyncIterator[RawBootstrapT]:
        for record in self._bootstrap:
            yield record


class NiceGuidelineAdapter(_BootstrapAdapter[JSONMapping]):
    source = "nice"

    async def fetch(self, licence: str | None = None) -> AsyncIterator[JSONMapping]:
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        params = {"licence": licence} if licence else None
        payload = await self.fetch_json("https://api.nice.org.uk/guidance", params=params or {})
        payload_map = ensure_json_mapping(payload, context="nice guidance response")
        items_value = payload_map.get("items", [])
        for record in ensure_json_sequence(items_value, context="nice guidance items"):
            yield ensure_json_mapping(record, context="nice guidance item")

    def parse(self, raw: JSONMapping) -> Document:
        payload: NiceGuidelineDocumentPayload = {
            "uid": str(raw.get("uid")) if raw.get("uid") is not None else "",
            "title": normalize_text(str(raw.get("title", ""))),
            "summary": normalize_text(str(raw.get("summary", ""))),
            "url": str(raw.get("url")) if isinstance(raw.get("url"), str) else None,
            "licence": str(raw.get("licence")) if isinstance(raw.get("licence"), str) else None,
        }
        if not payload["uid"]:
            raise ValueError("NICE guideline missing uid")
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=payload["uid"], version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=payload["summary"] or payload["title"],
            metadata={"uid": payload["uid"], "licence": payload["licence"]},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        licence = document.metadata.get("licence")
        if not isinstance(licence, str) or licence not in {"OpenGov", "CC-BY-ND"}:
            raise ValueError("Invalid NICE licence metadata")
        uid_meta = document.metadata.get("uid")
        if not isinstance(uid_meta, str) or not uid_meta:
            raise ValueError("NICE guideline missing uid metadata")


class UspstfAdapter(_BootstrapAdapter[JSONMapping]):
    source = "uspstf"

    async def fetch(self, *_: object, **__: object) -> AsyncIterator[JSONMapping]:
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        raise RuntimeError("USPSTF API requires manual approval; provide bootstrap records")

    def parse(self, raw: JSONMapping) -> Document:
        payload: UspstfDocumentPayload = {
            "id": str(raw.get("id")) if raw.get("id") is not None else None,
            "title": normalize_text(str(raw.get("title", ""))),
            "status": str(raw.get("status")) if isinstance(raw.get("status"), str) else None,
            "url": str(raw.get("url")) if isinstance(raw.get("url"), str) else None,
        }
        content = canonical_json(payload)
        identifier = payload["id"] or payload["title"]
        doc_id = self.build_doc_id(identifier=str(identifier), version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=payload["title"],
            metadata={"id": payload["id"], "status": payload["status"]},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        status = document.metadata.get("status")
        if not isinstance(status, str) or not status:
            raise ValueError("USPSTF record requires status")


class CdcSocrataAdapter(_BootstrapAdapter[JSONMapping]):
    source = "cdc_socrata"

    async def fetch(self, dataset: str, *, limit: int = 1000) -> AsyncIterator[JSONMapping]:
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        params = {"$limit": limit}
        payload = await self.fetch_json(f"https://data.cdc.gov/resource/{dataset}.json", params=params)
        rows = ensure_json_sequence(payload, context="cdc socrata rows")
        for row in rows:
            yield ensure_json_mapping(row, context="cdc socrata row")

    def parse(self, raw: JSONMapping) -> Document:
        identifier_value = raw.get("row_id")
        if isinstance(identifier_value, str) and identifier_value:
            identifier = identifier_value
        else:
            state = raw.get("state")
            year = raw.get("year")
            indicator = raw.get("indicator")
            identifier = f"{state}-{year}-{indicator}"
        payload: CdcSocrataDocumentPayload = {
            "identifier": identifier,
            "record": {key: cast(JSONValue, value) for key, value in raw.items()},
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=identifier, version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload["record"]),
            metadata={"identifier": identifier},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        if not document.metadata.get("identifier"):
            raise ValueError("CDC Socrata row missing identifier")


class CdcWonderAdapter(_BootstrapAdapter[str]):
    source = "cdc_wonder"

    async def fetch(self, *_: object, **__: object) -> AsyncIterator[str]:
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        raise RuntimeError("CDC WONDER requires XML form posts; provide bootstrap records")

    def parse(self, raw: str) -> Document:
        root = ET.fromstring(raw)
        rows = []
        for row in root.findall(".//row"):
            row_data: dict[str, str] = {}
            for child in list(row):
                row_data[child.tag] = normalize_text(child.text or "")
            rows.append(row_data)
        payload: CdcWonderDocumentPayload = {"rows": rows}
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(len(rows)), version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(rows),
            metadata={"rows": len(rows)},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        if document.metadata.get("rows", 0) == 0:
            raise ValueError("CDC WONDER payload contained no rows")


class WhoGhoAdapter(_BootstrapAdapter[JSONMapping]):
    source = "who_gho"

    async def fetch(self, indicator: str, *, spatial: str | None = None) -> AsyncIterator[JSONMapping]:
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        params = {"indicator": indicator}
        if spatial:
            params["spatial"] = spatial
        payload = await self.fetch_json("https://ghoapi.azureedge.net/api/GHO", params=params)
        payload_map = ensure_json_mapping(payload, context="who gho response")
        values_value = payload_map.get("value", [])
        for entry in ensure_json_sequence(values_value, context="who gho values"):
            yield ensure_json_mapping(entry, context="who gho entry")

    def parse(self, raw: JSONMapping) -> Document:
        payload: WhoGhoDocumentPayload = {
            "indicator": str(raw.get("Indicator")) if raw.get("Indicator") is not None else None,
            "value": cast(JSONValue, raw.get("Value")),
            "country": str(raw.get("SpatialDim")) if raw.get("SpatialDim") is not None else None,
            "year": str(raw.get("TimeDim")) if raw.get("TimeDim") is not None else None,
        }
        identifier = f"{payload['indicator']}-{payload['country']}-{payload['year']}"
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=identifier, version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload),
            metadata={"identifier": identifier},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        identifier = document.metadata.get("identifier")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("WHO GHO record missing identifier")


class OpenPrescribingAdapter(_BootstrapAdapter[JSONMapping]):
    source = "openprescribing"

    async def fetch(self, endpoint: str) -> AsyncIterator[JSONMapping]:
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        payload = await self.fetch_json(f"https://openprescribing.net/api/1.0/{endpoint}")
        rows = ensure_json_sequence(payload, context="openprescribing rows")
        for row in rows:
            yield ensure_json_mapping(row, context="openprescribing row")

    def parse(self, raw: JSONMapping) -> Document:
        identifier = (
            raw.get("row_id")
            or raw.get("practice")
            or json.dumps({key: raw[key] for key in sorted(raw)}, sort_keys=True)
        )
        identifier_str = str(identifier)
        payload: OpenPrescribingDocumentPayload = {
            "identifier": identifier_str,
            "record": {key: cast(JSONValue, value) for key, value in raw.items()},
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=identifier_str, version="v1", content=content)
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload["record"]),
            metadata={"identifier": identifier_str},
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        identifier = document.metadata.get("identifier")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("OpenPrescribing row missing identifier")
