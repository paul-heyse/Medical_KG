"""Typed wrapper around httpx supporting optional installation."""

from __future__ import annotations

import importlib
from datetime import timedelta
from types import ModuleType, TracebackType
from typing import Any, Protocol, cast


class ResponseProtocol(Protocol):
    """Subset of httpx.Response used in the codebase."""

    status_code: int
    text: str
    content: bytes
    elapsed: timedelta | None

    def json(self, **kwargs: Any) -> Any:
        ...

    def raise_for_status(self) -> None:
        ...


class StreamContextManager(Protocol):
    async def __aenter__(self) -> ResponseProtocol:
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        ...


class AsyncClientProtocol(Protocol):
    async def request(self, method: str, url: str, **kwargs: Any) -> ResponseProtocol:
        ...

    def stream(self, method: str, url: str, **kwargs: Any) -> StreamContextManager:
        ...

    async def aclose(self) -> None:
        ...


class ClientProtocol(Protocol):
    def get(self, url: str, **kwargs: Any) -> ResponseProtocol:
        ...

    def post(self, url: str, **kwargs: Any) -> ResponseProtocol:
        ...

    def close(self) -> None:
        ...


_httpx: ModuleType | None
try:  # pragma: no cover - exercised only when dependency available
    _httpx = importlib.import_module("httpx")
except ModuleNotFoundError:  # pragma: no cover - default for tests
    _httpx = None


if _httpx is not None:
    HTTPError = cast(type[Exception], getattr(_httpx, "HTTPError"))
else:  # pragma: no cover - executed when httpx missing
    class _HTTPError(Exception):
        """Fallback HTTPError when httpx is unavailable."""

        pass

    HTTPError = _HTTPError


def create_async_client(**kwargs: Any) -> AsyncClientProtocol:
    """Instantiate an AsyncClient with typed return value."""

    if _httpx is None:
        raise RuntimeError("httpx must be installed to create an AsyncClient")
    client = getattr(_httpx, "AsyncClient")(**kwargs)
    return cast(AsyncClientProtocol, client)


def create_client(**kwargs: Any) -> ClientProtocol:
    """Instantiate a Client with typed return value."""

    if _httpx is None:
        raise RuntimeError("httpx must be installed to create a Client")
    client = getattr(_httpx, "Client")(**kwargs)
    return cast(ClientProtocol, client)


__all__ = [
    "AsyncClientProtocol",
    "ClientProtocol",
    "HTTPError",
    "ResponseProtocol",
    "create_async_client",
    "create_client",
]
