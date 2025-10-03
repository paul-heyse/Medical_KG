from __future__ import annotations

import sys
from types import SimpleNamespace


class _DummyResponse:
    def __init__(self, status_code: int = 200) -> None:
        self.status_code = status_code

    def json(self) -> dict[str, object]:
        return {"data": []}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError("HTTP error")


class _DummyClient:
    def __init__(self, *_, **__) -> None:
        self._status = 200

    def __enter__(self) -> "_DummyClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def get(self, url: str) -> _DummyResponse:
        return _DummyResponse(self._status)

    def post(self, url: str, json: dict[str, object]) -> _DummyResponse:
        return _DummyResponse()

    def close(self) -> None:
        return None


sys.modules.setdefault("httpx", SimpleNamespace(Client=_DummyClient))
