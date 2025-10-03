from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator, Iterable, Sequence
from typing import Generic, Mapping, TypeVar, cast

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.adapters.http import HttpAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.payloads import (
    CdcSocrataRow,
    CdcWonderPayload,
    NiceGuidelinePayload,
    OpenPrescribingRow,
    UspstfPayload,
    WhoGhoDocumentPayload,
    WhoGhoPayload,
)
from Medical_KG.ingestion.utils import canonical_json, normalize_text

RawPayloadT = TypeVar("RawPayloadT")


class _BootstrapAdapter(HttpAdapter[RawPayloadT], Generic[RawPayloadT]):
    """Adapter base class that can iterate over bootstrap records."""

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[RawPayloadT] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def _yield_bootstrap(self) -> AsyncIterator[RawPayloadT]:
        for record in self._bootstrap:
            yield record


class NiceGuidelineAdapter(_BootstrapAdapter[NiceGuidelinePayload]):
    source = "nice"

    async def fetch(self, licence: str | None = None) -> AsyncIterator[NiceGuidelinePayload]:
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        params: dict[str, object] = {"licence": licence} if licence else {}
        payload = await self.fetch_json("https://api.nice.org.uk/guidance", params=params)
        data = cast(Mapping[str, object], payload if isinstance(payload, Mapping) else {})
        items = cast(Sequence[NiceGuidelinePayload], data.get("items") or [])
        for record in items:
            yield record

    def parse(self, raw: NiceGuidelinePayload) -> Document:
        payload: NiceGuidelinePayload = {
            "uid": raw.get("uid", ""),
            "title": normalize_text(raw.get("title", "")),
            "summary": normalize_text(raw.get("summary", "")),
            "url": raw.get("url"),
            "licence": raw.get("licence"),
        }
        if not payload["uid"]:
            raise ValueError("NICE guideline missing uid")
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=payload["uid"], version="v1", content=content)
        metadata: dict[str, object] = {"uid": payload["uid"], "licence": payload.get("licence") or ""}
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=payload["summary"] or payload["title"],
            metadata=metadata,
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        licence = document.metadata.get("licence")
        if licence not in {"OpenGov", "CC-BY-ND"}:
            raise ValueError("Invalid NICE licence metadata")
        if not document.metadata.get("uid"):
            raise ValueError("NICE guideline missing uid metadata")


class UspstfAdapter(_BootstrapAdapter[UspstfPayload]):
    source = "uspstf"

    async def fetch(self, *_: object, **__: object) -> AsyncIterator[UspstfPayload]:
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        raise RuntimeError("USPSTF API requires manual approval; provide bootstrap records")

    def parse(self, raw: UspstfPayload) -> Document:
        payload: UspstfPayload = {
            "id": raw.get("id", ""),
            "title": normalize_text(raw.get("title", "")),
            "status": raw.get("status"),
            "url": raw.get("url"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=payload["id"], version="v1", content=content)
        metadata: dict[str, object] = {"id": payload["id"], "status": payload.get("status") or ""}
        return Document(doc_id=doc_id, source=self.source, content=payload["title"], metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        if not document.metadata.get("status"):
            raise ValueError("USPSTF record requires status")


class CdcSocrataAdapter(_BootstrapAdapter[CdcSocrataRow]):
    source = "cdc_socrata"

    async def fetch(self, dataset: str, *, limit: int = 1000) -> AsyncIterator[CdcSocrataRow]:
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        params: dict[str, object] = {"$limit": limit}
        payload = await self.fetch_json(f"https://data.cdc.gov/resource/{dataset}.json", params=params)
        rows = cast(Sequence[CdcSocrataRow], payload if isinstance(payload, Sequence) else [])
        for row in rows:
            yield row

    def parse(self, raw: CdcSocrataRow) -> Document:
        payload: dict[str, object] = dict(raw)
        identifier = payload.get("row_id") or f"{payload.get('state')}-{payload.get('year')}-{payload.get('indicator')}"
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(identifier), version="v1", content=content)
        metadata: dict[str, object] = {"identifier": str(identifier)}
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata=metadata, raw=payload)

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
        rows: list[dict[str, str]] = []
        for row in root.findall(".//row"):
            row_data: dict[str, str] = {}
            for child in list(row):
                row_data[child.tag] = normalize_text(child.text or "")
            rows.append(row_data)
        payload: CdcWonderPayload = {"rows": rows}
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(len(rows)), version="v1", content=content)
        metadata: dict[str, object] = {"rows": len(rows)}
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(rows), metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        if document.metadata.get("rows", 0) == 0:
            raise ValueError("CDC WONDER payload contained no rows")


class WhoGhoAdapter(_BootstrapAdapter[WhoGhoPayload]):
    source = "who_gho"

    async def fetch(self, indicator: str, *, spatial: str | None = None) -> AsyncIterator[WhoGhoPayload]:
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        params: dict[str, object] = {"indicator": indicator}
        if spatial:
            params["spatial"] = spatial
        payload = await self.fetch_json("https://ghoapi.azureedge.net/api/GHO", params=params)
        data = cast(Mapping[str, object], payload if isinstance(payload, Mapping) else {})
        entries = cast(Sequence[WhoGhoPayload], data.get("value") or [])
        for entry in entries:
            yield entry

    def parse(self, raw: WhoGhoPayload) -> Document:
        payload: WhoGhoDocumentPayload = {
            "indicator": cast(str | None, raw.get("Indicator")),
            "value": cast(str | None, raw.get("Value")),
            "country": cast(str | None, raw.get("SpatialDim")),
            "year": cast(str | None, raw.get("TimeDim")),
        }
        identifier = f"{payload['indicator']}-{payload['country']}-{payload['year']}"
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=identifier, version="v1", content=content)
        metadata: dict[str, object] = {"identifier": identifier}
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        if not document.metadata.get("identifier"):
            raise ValueError("WHO GHO record missing identifier")


class OpenPrescribingAdapter(_BootstrapAdapter[OpenPrescribingRow]):
    source = "openprescribing"

    async def fetch(self, endpoint: str) -> AsyncIterator[OpenPrescribingRow]:
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        payload = await self.fetch_json(f"https://openprescribing.net/api/1.0/{endpoint}")
        rows = cast(Sequence[OpenPrescribingRow], payload if isinstance(payload, Sequence) else [])
        for row in rows:
            yield row

    def parse(self, raw: OpenPrescribingRow) -> Document:
        payload: dict[str, object] = dict(raw)
        identifier = payload.get("row_id") or payload.get("practice") or json.dumps(payload, sort_keys=True)
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(identifier), version="v1", content=content)
        metadata: dict[str, object] = {"identifier": str(identifier)}
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        if not document.metadata.get("identifier"):
            raise ValueError("OpenPrescribing row missing identifier")
