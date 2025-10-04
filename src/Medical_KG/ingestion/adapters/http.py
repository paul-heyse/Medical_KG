from __future__ import annotations

import time
from typing import Generic, Mapping, Sequence, TypeVar

from Medical_KG.compat.httpx import HTTPError
from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.events import AdapterRetry
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
        self.client.bind_retry_callback(self._handle_retry)

    def _handle_retry(
        self, method: str, url: str, attempt: int, error: Exception
    ) -> None:
        if not isinstance(error, HTTPError):  # pragma: no cover - defensive
            return
        status = getattr(getattr(error, "response", None), "status_code", None)
        self.emit_event(
            AdapterRetry(
                timestamp=time.time(),
                pipeline_id="",
                adapter=self.source,
                attempt=attempt,
                error=str(error),
                status_code=status,
            )
        )

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
