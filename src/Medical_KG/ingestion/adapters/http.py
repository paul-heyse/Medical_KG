from __future__ import annotations

from typing import Any, Mapping

from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient


class HttpAdapter(BaseAdapter):
    """Base class for HTTP-backed ingestion adapters."""

    def __init__(self, context: AdapterContext, client: AsyncHttpClient) -> None:
        super().__init__(context)
        self.client = client

    async def fetch_json(self, url: str, *, params: Mapping[str, Any] | None = None, headers: Mapping[str, str] | None = None) -> Any:
        return await self.client.get_json(url, params=params, headers=headers)

    async def fetch_text(self, url: str, *, params: Mapping[str, Any] | None = None, headers: Mapping[str, str] | None = None) -> str:
        return await self.client.get_text(url, params=params, headers=headers)

    async def fetch_bytes(
        self, url: str, *, params: Mapping[str, Any] | None = None, headers: Mapping[str, str] | None = None
    ) -> bytes:
        return await self.client.get_bytes(url, params=params, headers=headers)
