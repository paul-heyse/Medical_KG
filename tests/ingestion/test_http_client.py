import asyncio
from typing import Any

import pytest

import httpx
from Medical_KG.ingestion.http_client import AsyncHttpClient, RateLimit


class _MockTransport(httpx.AsyncBaseTransport):
    def __init__(self, responses: list[httpx.Response]) -> None:
        self._responses = responses
        self.calls: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:  # type: ignore[override]
        self.calls.append(request)
        response = self._responses.pop(0)
        if response.status_code >= 400:
            raise httpx.HTTPStatusError("error", request=request, response=response)
        return response


def test_retry_on_transient_failure(monkeypatch: Any) -> None:
    responses = [
        httpx.Response(status_code=502, request=httpx.Request("GET", "https://example.com")),
        httpx.Response(status_code=200, request=httpx.Request("GET", "https://example.com"), json={"ok": True}),
    ]
    transport = _MockTransport(responses)

    async def _request(self: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> httpx.Response:
        return await transport.handle_async_request(httpx.Request(method, url, **kwargs))

    client = AsyncHttpClient(retries=2, limits={"example.com": RateLimit(rate=5, per=1)})
    monkeypatch.setattr(client._client, "request", _request.__get__(client._client, httpx.AsyncClient))

    payload = asyncio.run(client.get_json("https://example.com"))
    assert payload == {"ok": True}
    assert len(transport.calls) == 2


def test_rate_limiter_serializes_calls(monkeypatch: Any) -> None:
    calls: list[float] = []

    async def _request(self: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> httpx.Response:
        calls.append(asyncio.get_running_loop().time())
        return httpx.Response(status_code=200, json={"ok": True}, request=httpx.Request(method, url, **kwargs))

    client = AsyncHttpClient(limits={"example.com": RateLimit(rate=1, per=0.5)})
    monkeypatch.setattr(client._client, "request", _request.__get__(client._client, httpx.AsyncClient))

    async def _run() -> None:
        await asyncio.gather(*(client.get_json("https://example.com") for _ in range(3)))

    asyncio.run(_run())
    assert len(calls) == 3
    assert all(b >= a for a, b in zip(calls, calls[1:]))


def test_timeout_propagates(monkeypatch: Any) -> None:
    async def _request(self: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> httpx.Response:
        raise httpx.TimeoutException("timeout", request=httpx.Request(method, url))

    client = AsyncHttpClient()
    monkeypatch.setattr(client._client, "request", _request.__get__(client._client, httpx.AsyncClient))

    async def _call() -> None:
        await client.get_json("https://example.com")

    with pytest.raises(httpx.TimeoutException):
        asyncio.run(_call())
