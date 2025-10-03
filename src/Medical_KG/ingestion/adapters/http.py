from __future__ import annotations

from typing import Mapping, TypeVar, Generic

from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.http_client import JsonValue


RawRecordT = TypeVar("RawRecordT")


class HttpAdapter(BaseAdapter[RawRecordT], Generic[RawRecordT]):
    """Base class for HTTP-backed ingestion adapters."""

    def __init__(self, context: AdapterContext, client: AsyncHttpClient) -> None:
        super().__init__(context)
        self.client = client

    async def fetch_json(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> JsonValue:
        return await self.client.get_json(url, params=params, headers=headers)

    async def fetch_text(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> str:
        return await self.client.get_text(url, params=params, headers=headers)

    async def fetch_bytes(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> bytes:
        return await self.client.get_bytes(url, params=params, headers=headers)
