"""Typed wrapper around httpx supporting optional installation."""

from __future__ import annotations

from datetime import timedelta
from types import TracebackType
from typing import Any, Protocol, cast

from Medical_KG.utils.optional_dependencies import MissingDependencyError, get_httpx_module


class ResponseProtocol(Protocol):
    """Subset of httpx.Response used in the codebase."""

    status_code: int
    text: str
    content: bytes
    elapsed: timedelta | None

    def json(self, **kwargs: Any) -> Any: ...

    def raise_for_status(self) -> None: ...


class StreamContextManager(Protocol):
    async def __aenter__(self) -> ResponseProtocol: ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...


class AsyncClientProtocol(Protocol):
    async def request(self, method: str, url: str, **kwargs: Any) -> ResponseProtocol: ...

    def stream(self, method: str, url: str, **kwargs: Any) -> StreamContextManager: ...

    async def aclose(self) -> None: ...


class ClientProtocol(Protocol):
    def get(self, url: str, **kwargs: Any) -> ResponseProtocol: ...

    def post(self, url: str, **kwargs: Any) -> ResponseProtocol: ...

    def close(self) -> None: ...


class _FallbackHTTPError(Exception):
    """Fallback HTTP error used when httpx is unavailable."""

    pass


HTTPError: type[Exception]

try:  # pragma: no cover - exercised only when dependency available
    HTTPError = cast(type[Exception], getattr(get_httpx_module(), "HTTPError"))
except MissingDependencyError:  # pragma: no cover - default for tests
    HTTPError = _FallbackHTTPError


def create_async_client(**kwargs: Any) -> AsyncClientProtocol:
    """Instantiate an AsyncClient with typed return value."""

    module = get_httpx_module()
    client = getattr(module, "AsyncClient")(**kwargs)
    return cast(AsyncClientProtocol, client)


def create_client(**kwargs: Any) -> ClientProtocol:
    """Instantiate a Client with typed return value."""

    module = get_httpx_module()
    client = getattr(module, "Client")(**kwargs)
    return cast(ClientProtocol, client)


__all__ = [
    "AsyncClientProtocol",
    "ClientProtocol",
    "HTTPError",
    "ResponseProtocol",
    "create_async_client",
    "create_client",
]
