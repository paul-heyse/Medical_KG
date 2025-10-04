from __future__ import annotations

import asyncio
from datetime import timedelta
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


def test_async_context_manager_closes_client(monkeypatch: Any) -> None:
    client = AsyncHttpClient()
    closed = False
    original_aclose = client._client.aclose

    async def _aclose() -> None:
        nonlocal closed
        closed = True
        await original_aclose()

    monkeypatch.setattr(client._client, "aclose", _aclose)

    async def _run() -> None:
        async with client:
            assert isinstance(client, AsyncHttpClient)

    asyncio.run(_run())
    assert closed is True


def test_async_context_manager_closes_on_exception(monkeypatch: Any) -> None:
    client = AsyncHttpClient()
    closed = False
    original_aclose = client._client.aclose

    async def _aclose() -> None:
        nonlocal closed
        closed = True
        await original_aclose()

    monkeypatch.setattr(client._client, "aclose", _aclose)

    async def _run() -> None:
        async with client:
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        asyncio.run(_run())
    assert closed is True


def test_nested_context_managers_close_in_reverse_order(monkeypatch: Any) -> None:
    outer = AsyncHttpClient()
    inner = AsyncHttpClient()
    order: list[str] = []

    outer_original = outer._client.aclose
    inner_original = inner._client.aclose

    async def _outer_close() -> None:
        order.append("outer")
        await outer_original()

    async def _inner_close() -> None:
        order.append("inner")
        await inner_original()

    monkeypatch.setattr(outer._client, "aclose", _outer_close)
    monkeypatch.setattr(inner._client, "aclose", _inner_close)

    async def _run() -> None:
        async with outer:
            async with inner:
                assert True

    asyncio.run(_run())
    assert order == ["inner", "outer"]


def test_http_client_uses_mock_transport(httpx_mock_transport: Any) -> None:
    def handler(request: HttpxRequestProtocol) -> HttpxResponseProtocol:
        assert request.method == "GET"
        return HTTPX.Response(
            status_code=200,
            json={"ok": True},
            request=request,
        )

    httpx_mock_transport(handler)

    async def _run() -> None:
        async with AsyncHttpClient() as client:
            payload = await client.get_json("https://example.com")
            assert payload.data["ok"] is True

    asyncio.run(_run())


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

    async def _request(
        self: HttpxAsyncClient, method: str, url: str, **kwargs: Any
    ) -> HttpxResponseProtocol:
        return await transport.handle_async_request(HTTPX.Request(method, url, **kwargs))

    client = AsyncHttpClient(retries=2, limits={"example.com": RateLimit(rate=5, per=1)})
    monkeypatch.setattr(
        client._client, "request", _request.__get__(client._client, HTTPX.AsyncClient)
    )

    async def _run() -> Any:
        async with client:
            return await client.get_json("https://example.com")

    payload = asyncio.run(_run())
    assert payload.data == {"ok": True}
    assert len(transport.calls) == 2


def test_rate_limiter_serializes_calls(monkeypatch: Any) -> None:
    calls: list[float] = []

    async def _request(
        self: HttpxAsyncClient, method: str, url: str, **kwargs: Any
    ) -> HttpxResponseProtocol:
        calls.append(asyncio.get_running_loop().time())
        return HTTPX.Response(
            status_code=200,
            json={"ok": True},
            request=HTTPX.Request(method, url, **kwargs),
        )

    client = AsyncHttpClient(limits={"example.com": RateLimit(rate=1, per=0.5)})
    monkeypatch.setattr(
        client._client, "request", _request.__get__(client._client, HTTPX.AsyncClient)
    )

    async def _run() -> None:
        async with client:
            await asyncio.gather(*(client.get_json("https://example.com") for _ in range(3)))

    asyncio.run(_run())
    assert len(calls) == 3
    assert all(b >= a for a, b in zip(calls, calls[1:]))


def test_timeout_propagates(monkeypatch: Any) -> None:
    async def _request(
        self: HttpxAsyncClient, method: str, url: str, **kwargs: Any
    ) -> HttpxResponseProtocol:
        raise HTTPX.TimeoutException("timeout")

    client = AsyncHttpClient()
    monkeypatch.setattr(
        client._client, "request", _request.__get__(client._client, HTTPX.AsyncClient)
    )

    async def _call() -> None:
        async with client:
            await client.get_json("https://example.com")

    with pytest.raises(HTTPX.TimeoutException):
        asyncio.run(_call())


def test_get_text_and_bytes(monkeypatch: Any) -> None:
    async def _request(
        self: HttpxAsyncClient, method: str, url: str, **kwargs: Any
    ) -> HttpxResponseProtocol:
        return HTTPX.Response(
            status_code=200,
            content=b"payload",
            request=HTTPX.Request(method, url, **kwargs),
        )

    client = AsyncHttpClient()
    monkeypatch.setattr(
        client._client, "request", _request.__get__(client._client, HTTPX.AsyncClient)
    )

    async def _run() -> None:
        async with client:
            text = await client.get_text("https://example.com")
            content = await client.get_bytes("https://example.com")
            assert text.text == "payload"
            assert content.content == b"payload"

    asyncio.run(_run())


def test_post_uses_execute(monkeypatch: Any) -> None:
    async def _request(
        self: HttpxAsyncClient, method: str, url: str, **kwargs: Any
    ) -> HttpxResponseProtocol:
        assert method == "POST"
        assert kwargs["json"] == {"value": 1}
        return HTTPX.Response(
            status_code=200, json={"ok": True}, request=HTTPX.Request(method, url, **kwargs)
        )

    client = AsyncHttpClient()
    monkeypatch.setattr(
        client._client, "request", _request.__get__(client._client, HTTPX.AsyncClient)
    )

    async def _run() -> None:
        async with client:
            response = await client.post("https://example.com", json={"value": 1})
            assert response.json()["ok"] is True

    asyncio.run(_run())


def test_stream_context_manager(monkeypatch: Any) -> None:
    response = HTTPX.Response(
        status_code=200,
        content=b"stream",
        request=HTTPX.Request("GET", "https://example.com"),
        extensions={"elapsed": timedelta(0)},
    )
    response._elapsed = timedelta(0)  # type: ignore[attr-defined]

    class _Stream:
        async def __aenter__(self) -> HttpxResponseProtocol:
            return response

        async def __aexit__(self, *_exc: Any) -> None:
            return None

    def _stream(self: HttpxAsyncClient, method: str, url: str, **kwargs: Any) -> Any:
        assert method == "GET"
        return _Stream()

    client = AsyncHttpClient()
    monkeypatch.setattr(
        client._client, "stream", _stream.__get__(client._client, HTTPX.AsyncClient)
    )

    async def _run() -> None:
        async with client:
            async with client.stream("GET", "https://example.com") as resp:
                assert resp.content == b"stream"

    asyncio.run(_run())


def test_set_rate_limit_resets_existing_limiter() -> None:
    client = AsyncHttpClient(limits={"example.com": RateLimit(rate=1, per=1.0)})
    first = client._get_limiter("example.com")
    client.set_rate_limit("example.com", RateLimit(rate=5, per=2.0))
    second = client._get_limiter("example.com")
    assert first is not second
    assert second.rate == 5
    asyncio.run(client.aclose())
