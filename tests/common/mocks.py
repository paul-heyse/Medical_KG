"""Reusable async transports and service doubles for tests."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, MutableMapping, Sequence

from Medical_KG.ingestion.models import IngestionResult
from Medical_KG.retrieval.models import RetrievalRequest, RetrievalResponse

@dataclass
class MockHttpResponse:
    """Payload configuration for :class:`MockAsyncHttpClient`."""

    json: Mapping[str, Any] | None = None
    text: str | None = None
    content: bytes | None = None
    status_code: int = 200


class MockAsyncHttpClient:
    """Async HTTP client double returning preconfigured payloads."""

    def __init__(self, responses: Mapping[str, MockHttpResponse]) -> None:
        self._responses: Dict[str, MockHttpResponse] = dict(responses)
        self.calls: list[tuple[str, Mapping[str, Any] | None]] = []

    async def get_json(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> Mapping[str, Any]:
        self.calls.append((url, params))
        response = self._responses.get(url)
        if response is None or response.json is None:
            raise KeyError(f"No JSON response configured for {url}")
        return response.json

    async def get_text(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> str:
        self.calls.append((url, params))
        response = self._responses.get(url)
        if response is None or response.text is None:
            raise KeyError(f"No text response configured for {url}")
        return response.text

    async def get_bytes(
        self,
        url: str,
        *,
        params: Mapping[str, Any] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> bytes:
        self.calls.append((url, params))
        response = self._responses.get(url)
        if response is None or response.content is None:
            raise KeyError(f"No bytes response configured for {url}")
        return response.content

    async def aclose(self) -> None:
        return None


@dataclass
class StubIngestionAdapter:
    """Adapter double returning predetermined ingestion results."""

    results: Sequence[IngestionResult] = field(default_factory=tuple)
    error: Exception | None = None
    calls: list[tuple[tuple[Any, ...], MutableMapping[str, Any]]] = field(default_factory=list)

    async def run(self, *args: Any, **kwargs: Any) -> list[IngestionResult]:
        self.calls.append((args, dict(kwargs)))
        if self.error is not None:
            raise self.error
        return list(self.results)


@dataclass
class StubRetrievalService:
    """Minimal async retrieval service suitable for dependency injection tests."""

    responses: Mapping[str, RetrievalResponse] | None = None
    default_response: RetrievalResponse | None = None
    delay: float = 0.0
    calls: list[RetrievalRequest] = field(default_factory=list)

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        self.calls.append(request)
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        if self.responses is not None and request.query in self.responses:
            return self.responses[request.query]
        if self.default_response is not None:
            return self.default_response
        raise KeyError(f"No retrieval response configured for query '{request.query}'")


__all__ = [
    "MockAsyncHttpClient",
    "MockHttpResponse",
    "StubIngestionAdapter",
    "StubRetrievalService",
]
