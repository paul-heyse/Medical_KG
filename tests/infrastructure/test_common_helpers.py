from __future__ import annotations

import asyncio

import pytest

from Medical_KG.retrieval.models import RetrievalRequest
from tests.common import (
    MockAsyncHttpClient,
    MockHttpResponse,
    StubIngestionAdapter,
    StubRetrievalService,
    make_ingestion_result,
    make_retrieval_request,
    make_retrieval_response,
)


def test_mock_http_client_returns_configured_payload() -> None:
    client = MockAsyncHttpClient({
        "https://example.com/json": MockHttpResponse(json={"ok": True}),
        "https://example.com/text": MockHttpResponse(text="payload"),
        "https://example.com/bytes": MockHttpResponse(content=b"data"),
    })

    async def _run() -> None:
        assert await client.get_json("https://example.com/json") == {"ok": True}
        assert await client.get_text("https://example.com/text") == "payload"
        assert await client.get_bytes("https://example.com/bytes") == b"data"

    asyncio.run(_run())
    assert [call[0] for call in client.calls] == [
        "https://example.com/json",
        "https://example.com/text",
        "https://example.com/bytes",
    ]


def test_mock_http_client_missing_payload_raises() -> None:
    client = MockAsyncHttpClient({})

    async def _run() -> None:
        with pytest.raises(KeyError):
            await client.get_json("https://missing")

    asyncio.run(_run())


def test_stub_ingestion_adapter_returns_results() -> None:
    result = make_ingestion_result()
    adapter = StubIngestionAdapter(results=[result])

    async def _run() -> None:
        payload = await adapter.run(limit=1)
        assert payload == [result]

    asyncio.run(_run())
    assert adapter.calls == [((), {"limit": 1})]


def test_stub_ingestion_adapter_raises_when_configured() -> None:
    adapter = StubIngestionAdapter(error=RuntimeError("boom"))

    async def _run() -> None:
        with pytest.raises(RuntimeError):
            await adapter.run()

    asyncio.run(_run())


def test_stub_retrieval_service_returns_mapping() -> None:
    request = make_retrieval_request(query="heart failure")
    response = make_retrieval_response(request=request)
    service = StubRetrievalService(responses={"heart failure": response})

    async def _run() -> None:
        payload = await service.retrieve(request)
        assert payload is response

    asyncio.run(_run())
    assert service.calls == [request]


def test_stub_retrieval_service_uses_default_response() -> None:
    default = make_retrieval_response()
    service = StubRetrievalService(default_response=default)
    request = RetrievalRequest(query="fallback")

    async def _run() -> None:
        payload = await service.retrieve(request)
        assert payload is default

    asyncio.run(_run())

    async def _missing() -> None:
        with pytest.raises(KeyError):
            await StubRetrievalService().retrieve(request)

    asyncio.run(_missing())
