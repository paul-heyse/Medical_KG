from __future__ import annotations

from typing import Generic, Mapping, Sequence, TypeVar

from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.telemetry import HttpTelemetry
from Medical_KG.ingestion.types import JSONValue

RawPayloadT = TypeVar("RawPayloadT")


class HttpAdapter(BaseAdapter[RawPayloadT], Generic[RawPayloadT]):
    """Base class for HTTP-backed ingestion adapters."""

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        telemetry: (
            HttpTelemetry
            | Sequence[HttpTelemetry]
            | Mapping[str, HttpTelemetry | Sequence[HttpTelemetry]]
        )
        | None = None,
    ) -> None:
        super().__init__(context)
        self.client = client
        if telemetry is not None:
            self.client.add_telemetry(telemetry)

    async def fetch_json(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> JSONValue:
        response = await self.client.get_json(url, params=params, headers=headers)
        return response.data

    async def fetch_text(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> str:
        response = await self.client.get_text(url, params=params, headers=headers)
        return response.text

    async def fetch_bytes(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> bytes:
        response = await self.client.get_bytes(url, params=params, headers=headers)
        return response.content
