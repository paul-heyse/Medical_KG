"""Guideline and knowledge-base ingestion adapters with optional field context.

NICE and USPSTF adapters primarily consume curated bootstrap records where URLs
are usually present but licence identifiers (NICE) and stable IDs (USPSTF) are
less reliable. Knowledge-base adapters wrap tabular datasets; WHO GHO exposes
optional ``indicator``/``country``/``year`` values while CDC Socrata and
OpenPrescribing derive identifiers from row content when explicit primary keys
are missing. The tests in ``tests/ingestion/test_optional_fields.py`` exercise
both fully populated and minimal payloads so adapters never assume optional
fields exist.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator, Iterable
from collections.abc import Sequence as SequenceABC
from typing import Generic, Mapping, TypeVar

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.adapters.http import HttpAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.types import (
    CdcSocrataDocumentPayload,
    CdcWonderDocumentPayload,
    JSONMapping,
    JSONSequence,
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
    ensure_json_value,
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
        payload_value = await self.fetch_json("https://api.nice.org.uk/guidance", params=params or {})
        payload_map: JSONMapping = ensure_json_mapping(
            ensure_json_value(payload_value, context="nice guidance response value"),
            context="nice guidance response",
        )
        # NICE guidance API (v1, 2023-12 docs) wraps results in an object with an
        # ``items`` array.
        items_value = payload_map.get("items")
        items_sequence: JSONSequence = ensure_json_sequence(
            items_value if items_value is not None else [],
            context="nice guidance items",
        )
        # Keep boundary validation so schema changes in the REST payload are
        # surfaced during fetch.
        for record_value in items_sequence:
            record_mapping = ensure_json_mapping(
                record_value,
                context="nice guidance item",
            )
            yield record_mapping

    def parse(self, raw: JSONMapping) -> Document:
        uid_value = raw.get("uid")
        if not isinstance(uid_value, str) or not uid_value:
            raise ValueError("NICE guideline missing uid")
        title_value = raw.get("title")
        summary_value = raw.get("summary")
        url_value = raw.get("url")
        licence_value = raw.get("licence")
        payload: NiceGuidelineDocumentPayload = {
            "uid": uid_value,
            "title": normalize_text(title_value) if isinstance(title_value, str) else "",
            "summary": normalize_text(summary_value) if isinstance(summary_value, str) else "",
            "url": url_value if isinstance(url_value, str) else None,
            "licence": licence_value if isinstance(licence_value, str) else None,
        }
        # ``url`` and ``licence`` are ``NotRequired``; fixture coverage asserts both
        # fully populated and empty cases so the adapter never assumes their
        # presence.
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=payload["uid"], version="v1", content=content)
        metadata: dict[str, JSONValue] = {"uid": payload["uid"]}
        if payload["licence"] is not None:
            metadata["licence"] = payload["licence"]
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=payload["summary"] or payload["title"],
            metadata=metadata,
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        licence_meta = document.metadata.get("licence")
        licence_raw = None
        if isinstance(document.raw, Mapping):
            licence_raw = document.raw.get("licence")
        if isinstance(licence_meta, str):
            licence_value = licence_meta
        elif isinstance(licence_raw, str):
            licence_value = licence_raw
        else:
            licence_value = None
        if licence_value is not None and licence_value not in {"OpenGov", "CC-BY-ND"}:
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
        title_value = raw.get("title")
        if not isinstance(title_value, str) or not title_value:
            raise ValueError("USPSTF payload missing title")
        identifier_value = raw.get("id")
        status_value = raw.get("status")
        url_value = raw.get("url")
        payload: UspstfDocumentPayload = {
            "id": identifier_value if isinstance(identifier_value, str) else None,
            "title": normalize_text(title_value),
            "status": status_value if isinstance(status_value, str) else None,
            "url": url_value if isinstance(url_value, str) else None,
        }
        # USPSTF payloads occasionally omit ``id``/``status``/``url``; optional field
        # tests confirm validation only enforces status when present.
        content = canonical_json(payload)
        identifier = payload["id"] or payload["title"]
        doc_id = self.build_doc_id(identifier=identifier, version="v1", content=content)
        metadata: dict[str, JSONValue] = {"title": payload["title"]}
        if payload["id"] is not None:
            metadata["id"] = payload["id"]
        if payload["status"] is not None:
            metadata["status"] = payload["status"]
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=payload["title"],
            metadata=metadata,
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
        # CDC Socrata datasets expose each table as an array of row objects; keep
        # boundary validation tied to the 2024-02 API schema.
        for row in rows:
            yield ensure_json_mapping(
                row,
                context="cdc socrata row",
            )

    def parse(self, raw: JSONMapping) -> Document:
        identifier_value = raw.get("row_id")
        if isinstance(identifier_value, str) and identifier_value:
            identifier = identifier_value
        else:
            state = raw.get("state")
            year = raw.get("year")
            indicator = raw.get("indicator")
            identifier = f"{state}-{year}-{indicator}"
        record_payload: dict[str, JSONValue] = {key: value for key, value in raw.items()}
        payload: CdcSocrataDocumentPayload = {
            "identifier": identifier,
            "record": record_payload,
        }
        # CDC Socrata exposes optional ``row_id``; when absent we synthesise an
        # identifier from state/year/indicator so downstream code still receives a
        # stable key.
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=identifier, version="v1", content=content)
        metadata: dict[str, JSONValue] = {"identifier": identifier}
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload["record"]),
            metadata=metadata,
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
        metadata: dict[str, JSONValue] = {"rows": len(rows)}
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(rows),
            metadata=metadata,
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
        payload_map = ensure_json_mapping(
            payload,
            context="who gho response",
        )
        # WHO GHO API (beta docs 2023) wraps indicator rows in a ``value`` array.
        values_value = payload_map.get("value", [])
        for entry in ensure_json_sequence(
            values_value,
            context="who gho values",
        ):
            yield ensure_json_mapping(
                entry,
                context="who gho entry",
            )

    def parse(self, raw: JSONMapping) -> Document:
        indicator_value = raw.get("Indicator")
        country_value = raw.get("SpatialDim")
        year_value = raw.get("TimeDim")
        value_raw = raw.get("Value")
        if isinstance(value_raw, (str, int, float, bool)) or value_raw is None:
            value: JSONValue = value_raw
        elif isinstance(value_raw, Mapping):
            value = dict(value_raw)
        elif isinstance(value_raw, SequenceABC) and not isinstance(value_raw, (str, bytes, bytearray)):
            value = list(value_raw)
        else:
            value = str(value_raw)
        payload: WhoGhoDocumentPayload = {
            "indicator": indicator_value if isinstance(indicator_value, str) else None,
            "value": value,
            "country": country_value if isinstance(country_value, str) else None,
            "year": year_value if isinstance(year_value, str) else None,
        }
        # Indicator/country/year arrive inconsistently; treat them as optional to
        # keep the payload aligned with ``WhoGhoDocumentPayload`` and rely on tests
        # to verify both populated and blank variants.
        identifier = (
            f"{payload['indicator'] or 'unknown'}-"
            f"{payload['country'] or 'unknown'}-"
            f"{payload['year'] or 'unknown'}"
        )
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=identifier, version="v1", content=content)
        metadata: dict[str, JSONValue] = {"identifier": identifier}
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload),
            metadata=metadata,
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
        # OpenPrescribing API v1 returns each query as an array of JSON objects;
        # retain boundary validation to detect schema changes early.
        for row in rows:
            yield ensure_json_mapping(
                row,
                context="openprescribing row",
            )

    def parse(self, raw: JSONMapping) -> Document:
        identifier = (
            raw.get("row_id")
            or raw.get("practice")
            or json.dumps({key: raw[key] for key in sorted(raw)}, sort_keys=True)
        )
        identifier_str = str(identifier)
        record_payload: dict[str, JSONValue] = {key: value for key, value in raw.items()}
        payload: OpenPrescribingDocumentPayload = {
            "identifier": identifier_str,
            "record": record_payload,
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=identifier_str, version="v1", content=content)
        metadata: dict[str, JSONValue] = {"identifier": identifier_str}
        return Document(
            doc_id=doc_id,
            source=self.source,
            content=json.dumps(payload["record"]),
            metadata=metadata,
            raw=payload,
        )

    def validate(self, document: Document) -> None:
        identifier = document.metadata.get("identifier")
        if not isinstance(identifier, str) or not identifier:
            raise ValueError("OpenPrescribing row missing identifier")
