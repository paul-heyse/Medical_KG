from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import Any, Sequence, cast

import pytest

from Medical_KG.ingestion.http_client import AsyncHttpClient, RateLimit
from Medical_KG.ingestion.telemetry import (
    HttpBackoffEvent,
    HttpErrorEvent,
    HttpRequestEvent,
    HttpResponseEvent,
    HttpRetryEvent,
)
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


class _RecordingTelemetry:
    def __init__(self) -> None:
        self.events: list[tuple[str, object]] = []

    def on_request(self, event: HttpRequestEvent) -> None:
        self.events.append(("request", event))

    def on_response(self, event: HttpResponseEvent) -> None:
        self.events.append(("response", event))

    def on_retry(self, event: HttpRetryEvent) -> None:
        self.events.append(("retry", event))

    def on_backoff(self, event: HttpBackoffEvent) -> None:
        self.events.append(("backoff", event))

    def on_error(self, event: HttpErrorEvent) -> None:
        self.events.append(("error", event))


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


def test_http_client_emits_events(monkeypatch: Any) -> None:
    telemetry = _RecordingTelemetry()

    async def _request(
        self: HttpxAsyncClient, method: str, url: str, **kwargs: Any
    ) -> HttpxResponseProtocol:
        return HTTPX.Response(
            status_code=200,
            json={"ok": True},
            request=HTTPX.Request(method, url, **kwargs),
        )

    client = AsyncHttpClient(telemetry=[telemetry])
    monkeypatch.setattr(
        client._client, "request", _request.__get__(client._client, HTTPX.AsyncClient)
    )

    async def _run() -> None:
        async with client:
            await client.get_json("https://example.com/data")

    asyncio.run(_run())

    event_names = [name for name, _ in telemetry.events]
    assert event_names[:3] == ["backoff", "request", "response"]
    request_event = cast(HttpRequestEvent, telemetry.events[1][1])
    assert request_event.method == "GET"
    assert request_event.url == "https://example.com/data"
    response_event = cast(HttpResponseEvent, telemetry.events[2][1])
    assert response_event.status_code == 200


def test_http_client_emits_error_event(monkeypatch: Any) -> None:
    telemetry = _RecordingTelemetry()

    async def _request(
        self: HttpxAsyncClient, method: str, url: str, **kwargs: Any
    ) -> HttpxResponseProtocol:
        raise HTTPX.TimeoutException("boom")

    client = AsyncHttpClient(telemetry=[telemetry])
    monkeypatch.setattr(
        client._client, "request", _request.__get__(client._client, HTTPX.AsyncClient)
    )

    async def _call() -> None:
        async with client:
            await client.get_json("https://example.com/failure")

    with pytest.raises(HTTPX.TimeoutException):
        asyncio.run(_call())

    assert telemetry.events[-1][0] == "error"
    error_event = cast(HttpErrorEvent, telemetry.events[-1][1])
    assert error_event.retryable is False


def test_http_client_emits_retry_event(monkeypatch: Any) -> None:
    telemetry = _RecordingTelemetry()
    responses = [
        HTTPX.Response(status_code=502, request=HTTPX.Request("GET", "https://example.com")),
        HTTPX.Response(
            status_code=200,
            json={"ok": True},
            request=HTTPX.Request("GET", "https://example.com"),
        ),
    ]

    async def _request(
        self: HttpxAsyncClient, method: str, url: str, **kwargs: Any
    ) -> HttpxResponseProtocol:
        return responses.pop(0)

    client = AsyncHttpClient(retries=2, telemetry=[telemetry])
    monkeypatch.setattr(
        client._client, "request", _request.__get__(client._client, HTTPX.AsyncClient)
    )

    async def _run() -> None:
        async with client:
            await client.get_json("https://example.com")

    asyncio.run(_run())

    retry_events = [event for name, event in telemetry.events if name == "retry"]
    assert len(retry_events) == 1
    retry_event = cast(HttpRetryEvent, retry_events[0])
    assert retry_event.attempt == 1
    assert retry_event.reason == "status_502"
    assert retry_event.will_retry is True
    error_event = cast(HttpErrorEvent, next(event for name, event in telemetry.events if name == "error"))
    assert error_event.retryable is True


def test_backoff_event_contains_queue_metrics(monkeypatch: Any) -> None:
    telemetry = _RecordingTelemetry()

    async def _request(
        self: HttpxAsyncClient, method: str, url: str, **kwargs: Any
    ) -> HttpxResponseProtocol:
        return HTTPX.Response(
            status_code=200,
            json={"ok": True},
            request=HTTPX.Request(method, url, **kwargs),
        )

    client = AsyncHttpClient(
        limits={"example.com": RateLimit(rate=1, per=0.01)}, telemetry=[telemetry]
    )
    monkeypatch.setattr(
        client._client, "request", _request.__get__(client._client, HTTPX.AsyncClient)
    )

    async def _run() -> None:
        async with client:
            await client.get_json("https://example.com/one")
            await client.get_json("https://example.com/one")

    asyncio.run(_run())

    backoff_events = [
        cast(HttpBackoffEvent, event)
        for name, event in telemetry.events
        if name == "backoff"
    ]
    assert len(backoff_events) == 2
    assert backoff_events[0].queue_capacity == 1
    assert backoff_events[1].wait_time_seconds >= 0.005


def test_callback_exceptions_do_not_break_requests(monkeypatch: Any) -> None:
    seen: list[HttpResponseEvent] = []

    def _raise(_: HttpRequestEvent) -> None:
        raise RuntimeError("no telemetry")

    def _record(event: HttpResponseEvent) -> None:
        seen.append(event)

    async def _request(
        self: HttpxAsyncClient, method: str, url: str, **kwargs: Any
    ) -> HttpxResponseProtocol:
        return HTTPX.Response(
            status_code=200,
            json={"ok": True},
            request=HTTPX.Request(method, url, **kwargs),
        )

    client = AsyncHttpClient(on_request=_raise, on_response=_record)
    monkeypatch.setattr(
        client._client, "request", _request.__get__(client._client, HTTPX.AsyncClient)
    )

    async def _run() -> None:
        async with client:
            await client.get_json("https://example.com")

    asyncio.run(_run())
    assert seen


def test_host_specific_telemetry(monkeypatch: Any) -> None:
    example_calls: list[str] = []
    other_calls: list[str] = []

    class _SimpleTelemetry(_RecordingTelemetry):
        def __init__(self, bucket: list[str]) -> None:
            super().__init__()
            self._bucket = bucket

        def on_request(self, event: HttpRequestEvent) -> None:
            self._bucket.append(event.host)

    telemetry = {
        "example.com": _SimpleTelemetry(example_calls),
        "other.com": _SimpleTelemetry(other_calls),
    }

    async def _request(
        self: HttpxAsyncClient, method: str, url: str, **kwargs: Any
    ) -> HttpxResponseProtocol:
        return HTTPX.Response(
            status_code=200,
            json={},
            request=HTTPX.Request(method, url, **kwargs),
        )

    client = AsyncHttpClient()
    client.add_telemetry(telemetry)
    monkeypatch.setattr(
        client._client, "request", _request.__get__(client._client, HTTPX.AsyncClient)
    )

    async def _run() -> None:
        async with client:
            await client.get_json("https://example.com/path")
            await client.get_json("https://other.com/path")

    asyncio.run(_run())
    assert example_calls == ["example.com"]
    assert other_calls == ["other.com"]


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
