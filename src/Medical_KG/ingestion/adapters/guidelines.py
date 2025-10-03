from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator, Iterable
from typing import Any

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.adapters.http import HttpAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.utils import canonical_json, normalize_text


class _BootstrapAdapter(HttpAdapter):
    """Adapter base class that can iterate over bootstrap records."""

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[Any] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def _yield_bootstrap(self) -> AsyncIterator[Any]:
        for record in self._bootstrap:
            yield record


class NiceGuidelineAdapter(_BootstrapAdapter):
    source = "nice"

    async def fetch(self, licence: str | None = None) -> AsyncIterator[Any]:  # pragma: no cover - integration-only path
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        params = {"licence": licence} if licence else None
        payload = await self.fetch_json("https://api.nice.org.uk/guidance", params=params or {})
        for record in payload.get("items", []):
            yield record

    def parse(self, raw: Any) -> Document:
        payload = {
            "uid": raw.get("uid"),
            "title": normalize_text(raw.get("title", "")),
            "summary": normalize_text(raw.get("summary", "")),
            "url": raw.get("url"),
            "licence": raw.get("licence"),
        }
        if not payload["uid"]:
            raise ValueError("NICE guideline missing uid")
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=payload["uid"], version="v1", content=content)
        return Document(doc_id=doc_id, source=self.source, content=payload["summary"] or payload["title"], metadata={"uid": payload["uid"], "licence": payload["licence"]}, raw=payload)

    def validate(self, document: Document) -> None:
        licence = document.metadata.get("licence")
        if licence not in {"OpenGov", "CC-BY-ND"}:
            raise ValueError("Invalid NICE licence metadata")
        if not document.metadata.get("uid"):
            raise ValueError("NICE guideline missing uid metadata")


class UspstfAdapter(_BootstrapAdapter):
    source = "uspstf"

    async def fetch(self, *_: Any, **__: Any) -> AsyncIterator[Any]:  # pragma: no cover - integration-only path
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        raise RuntimeError("USPSTF API requires manual approval; provide bootstrap records")

    def parse(self, raw: Any) -> Document:
        payload = {
            "id": raw.get("id"),
            "title": normalize_text(raw.get("title", "")),
            "status": raw.get("status"),
            "url": raw.get("url"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=payload["id"], version="v1", content=content)
        return Document(doc_id=doc_id, source=self.source, content=payload["title"], metadata={"id": payload["id"], "status": payload["status"]}, raw=payload)

    def validate(self, document: Document) -> None:
        if not document.metadata.get("status"):
            raise ValueError("USPSTF record requires status")


class CdcSocrataAdapter(_BootstrapAdapter):
    source = "cdc_socrata"

    async def fetch(self, dataset: str, *, limit: int = 1000) -> AsyncIterator[Any]:  # pragma: no cover - integration-only path
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        params = {"$limit": limit}
        payload = await self.fetch_json(f"https://data.cdc.gov/resource/{dataset}.json", params=params)
        for row in payload:
            yield row

    def parse(self, raw: Any) -> Document:
        payload = dict(raw)
        identifier = payload.get("row_id") or f"{payload.get('state')}-{payload.get('year')}-{payload.get('indicator')}"
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=identifier, version="v1", content=content)
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata={"identifier": identifier}, raw=payload)

    def validate(self, document: Document) -> None:
        if not document.metadata.get("identifier"):
            raise ValueError("CDC Socrata row missing identifier")


class CdcWonderAdapter(_BootstrapAdapter):
    source = "cdc_wonder"

    async def fetch(self, *_: Any, **__: Any) -> AsyncIterator[Any]:  # pragma: no cover - integration-only path
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        raise RuntimeError("CDC WONDER requires XML form posts; provide bootstrap records")

    def parse(self, raw: Any) -> Document:
        root = ET.fromstring(raw)
        rows = []
        for row in root.findall(".//row"):
            row_data: dict[str, str] = {}
            for child in list(row):
                row_data[child.tag] = normalize_text(child.text or "")
            rows.append(row_data)
        payload = {"rows": rows}
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=str(len(rows)), version="v1", content=content)
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(rows), metadata={"rows": len(rows)}, raw=payload)

    def validate(self, document: Document) -> None:
        if document.metadata.get("rows", 0) == 0:
            raise ValueError("CDC WONDER payload contained no rows")


class WhoGhoAdapter(_BootstrapAdapter):
    source = "who_gho"

    async def fetch(self, indicator: str, *, spatial: str | None = None) -> AsyncIterator[Any]:  # pragma: no cover - integration-only path
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        params = {"indicator": indicator}
        if spatial:
            params["spatial"] = spatial
        payload = await self.fetch_json("https://ghoapi.azureedge.net/api/GHO", params=params)
        for entry in payload.get("value", []):
            yield entry

    def parse(self, raw: Any) -> Document:
        payload = {
            "indicator": raw.get("Indicator"),
            "value": raw.get("Value"),
            "country": raw.get("SpatialDim"),
            "year": raw.get("TimeDim"),
        }
        identifier = f"{payload['indicator']}-{payload['country']}-{payload['year']}"
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=identifier, version="v1", content=content)
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata={"identifier": identifier}, raw=payload)

    def validate(self, document: Document) -> None:
        if not document.metadata.get("identifier"):
            raise ValueError("WHO GHO record missing identifier")


class OpenPrescribingAdapter(_BootstrapAdapter):
    source = "openprescribing"

    async def fetch(self, endpoint: str) -> AsyncIterator[Any]:  # pragma: no cover - integration-only path
        if self._bootstrap:
            async for record in self._yield_bootstrap():
                yield record
            return
        payload = await self.fetch_json(f"https://openprescribing.net/api/1.0/{endpoint}")
        for row in payload:
            yield row

    def parse(self, raw: Any) -> Document:
        payload = dict(raw)
        identifier = payload.get("row_id") or payload.get("practice") or json.dumps(payload, sort_keys=True)
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=identifier, version="v1", content=content)
        return Document(doc_id=doc_id, source=self.source, content=json.dumps(payload), metadata={"identifier": identifier}, raw=payload)

    def validate(self, document: Document) -> None:
        if not document.metadata.get("identifier"):
            raise ValueError("OpenPrescribing row missing identifier")
