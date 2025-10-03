import asyncio
from typing import Any
import asyncio
from typing import Any

import pytest

import httpx
from Medical_KG.ingestion.http_client import AsyncHttpClient, RateLimit


class TestTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"ok": True})


def test_retry_on_transient_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = [
        httpx.Response(status_code=502, request=httpx.Request("GET", "https://example.com")),
        httpx.Response(status_code=200, request=httpx.Request("GET", "https://example.com"), json={"ok": True}),
    ]
    calls: list[httpx.Request] = []

    async def _request(self: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> httpx.Response:
        request = httpx.Request(method, url, **kwargs)
        calls.append(request)
        response = responses.pop(0)
        return response

    client = AsyncHttpClient(retries=2, limits={"example.com": RateLimit(rate=5, per=1)})
    monkeypatch.setattr(client._client, "request", _request.__get__(client._client, httpx.AsyncClient))

    payload = asyncio.run(client.get_json("https://example.com"))
    assert payload == {"ok": True}
    assert len(calls) == 2
    asyncio.run(client.aclose())


def test_rate_limiter_serializes_calls(monkeypatch: pytest.MonkeyPatch) -> None:
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
    asyncio.run(client.aclose())


def test_timeout_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _request(self: httpx.AsyncClient, method: str, url: str, **kwargs: Any) -> httpx.Response:
        raise httpx.TimeoutException("timeout", request=httpx.Request(method, url))

    client = AsyncHttpClient()
    monkeypatch.setattr(client._client, "request", _request.__get__(client._client, httpx.AsyncClient))

    async def _call() -> None:
        await client.get_json("https://example.com")

    with pytest.raises(httpx.TimeoutException):
        asyncio.run(_call())
    asyncio.run(client.aclose())
