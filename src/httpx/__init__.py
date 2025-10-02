from __future__ import annotations

import json
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any, AsyncIterator, Dict, Optional


class HTTPError(Exception):
    """Base HTTP error."""


class HTTPStatusError(HTTPError):
    def __init__(self, message: str, *, request: Request | None = None, response: Response | None = None) -> None:
        super().__init__(message)
        self.request = request
        self.response = response


class TimeoutException(HTTPError):
    def __init__(self, message: str, *, request: Request | None = None) -> None:
        super().__init__(message)
        self.request = request


@dataclass
class Request:
    method: str
    url: str
    headers: Dict[str, str] = field(default_factory=dict)
    data: Any | None = None
    params: Any | None = None


class Response:
    def __init__(
        self,
        *,
        status_code: int,
        request: Request | None = None,
        json: Any | None = None,
        text: str | None = None,
        content: bytes | None = None,
    ) -> None:
        self.status_code = status_code
        self.request = request
        self._json = json
        self._text = text
        self._content = content
        self.elapsed: Optional[timedelta] = None

    def json(self) -> Any:
        if self._json is not None:
            return self._json
        if self._text is not None:
            return json.loads(self._text)
        if self._content is not None:
            return json.loads(self._content.decode("utf-8"))
        raise ValueError("No JSON payload available")

    @property
    def text(self) -> str:
        if self._text is not None:
            return self._text
        if self._content is not None:
            return self._content.decode("utf-8")
        if self._json is not None:
            return json.dumps(self._json)
        return ""

    @property
    def content(self) -> bytes:
        if self._content is not None:
            return self._content
        return self.text.encode("utf-8")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise HTTPStatusError("HTTP error", request=self.request, response=self)


class AsyncBaseTransport:
    async def handle_async_request(self, request: Request) -> Response:
        raise NotImplementedError


class AsyncClient:
    def __init__(self, *, timeout: float | None = None, headers: Dict[str, str] | None = None, http2: bool = False) -> None:
        self.timeout = timeout
        self.headers = headers or {}
        self.http2 = http2

    async def request(self, method: str, url: str, **kwargs: Any) -> Response:
        raise NotImplementedError("Provide transport or monkeypatch request() in tests")

    async def aclose(self) -> None:  # pragma: no cover - compatibility
        return None

    @asynccontextmanager
    async def stream(self, method: str, url: str, **kwargs: Any) -> AsyncIterator[Response]:
        response = await self.request(method, url, **kwargs)
        yield response
