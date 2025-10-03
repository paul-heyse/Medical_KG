from __future__ import annotations

import asyncio
from typing import Any, Sequence

import pytest

from Medical_KG.ingestion.http_client import AsyncHttpClient, RateLimit
from Medical_KG.utils.optional_dependencies import (
    HttpxAsyncClient,
    HttpxModule,
    HttpxRequestProtocol,
    HttpxResponseProtocol,
    get_httpx_module,
)

HTTPX: HttpxModule = get_httpx_module()


class _MockTransport:
    def __init__(self, responses: Sequence[HttpxResponseProtocol]) -> None:
        self._responses = list(responses)
        self.calls: list[str] = []

    async def handle_async_request(self, request: HttpxRequestProtocol) -> HttpxResponseProtocol:
        self.calls.append(str(request.url))
        return self._responses.pop(0)


def test_retry_on_transient_failure(monkeypatch: Any) -> None:
    responses = [
        HTTPX.Response(status_code=502, request=HTTPX.Request("GET", "https://example.com")),
        HTTPX.Response(
            status_code=200,
            request=HTTPX.Request("GET", "https://example.com"),
            json={"ok": True},
        ),
    ]
    transport = _MockTransport(responses)

    async def _request(self: HttpxAsyncClient, method: str, url: str, **kwargs: Any) -> HttpxResponseProtocol:
        return await transport.handle_async_request(HTTPX.Request(method, url, **kwargs))

    client = AsyncHttpClient(retries=2, limits={"example.com": RateLimit(rate=5, per=1)})
    monkeypatch.setattr(client._client, "request", _request.__get__(client._client, HTTPX.AsyncClient))

    payload = asyncio.run(client.get_json("https://example.com"))
    assert payload == {"ok": True}
    assert len(transport.calls) == 2


def test_rate_limiter_serializes_calls(monkeypatch: Any) -> None:
    calls: list[float] = []

    async def _request(self: HttpxAsyncClient, method: str, url: str, **kwargs: Any) -> HttpxResponseProtocol:
        calls.append(asyncio.get_running_loop().time())
        return HTTPX.Response(
            status_code=200,
            json={"ok": True},
            request=HTTPX.Request(method, url, **kwargs),
        )

    client = AsyncHttpClient(limits={"example.com": RateLimit(rate=1, per=0.5)})
    monkeypatch.setattr(client._client, "request", _request.__get__(client._client, HTTPX.AsyncClient))

    async def _run() -> None:
        await asyncio.gather(*(client.get_json("https://example.com") for _ in range(3)))

    asyncio.run(_run())
    assert len(calls) == 3
    assert all(b >= a for a, b in zip(calls, calls[1:]))


def test_timeout_propagates(monkeypatch: Any) -> None:
    async def _request(self: HttpxAsyncClient, method: str, url: str, **kwargs: Any) -> HttpxResponseProtocol:
        raise HTTPX.TimeoutException("timeout")

    client = AsyncHttpClient()
    monkeypatch.setattr(client._client, "request", _request.__get__(client._client, HTTPX.AsyncClient))

    async def _call() -> None:
        await client.get_json("https://example.com")

    with pytest.raises(HTTPX.TimeoutException):
        asyncio.run(_call())
