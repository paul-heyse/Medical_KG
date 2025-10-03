from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest


class _MetricStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, str] | float]] = []

    def labels(self, **labels: str) -> "_MetricStub":
        self.calls.append(("labels", labels))
        return self

    def inc(self, amount: float = 1.0) -> None:
        self.calls.append(("inc", amount))

    def observe(self, value: float) -> None:
        self.calls.append(("observe", value))


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


@pytest.fixture(autouse=True)
def stub_embedding_metrics(monkeypatch: pytest.MonkeyPatch) -> dict[str, _MetricStub]:
    requests = _MetricStub()
    errors = _MetricStub()
    latency = _MetricStub()
    monkeypatch.setattr("Medical_KG.embeddings.metrics.EMBEDDING_REQUESTS", requests)
    monkeypatch.setattr("Medical_KG.embeddings.metrics.EMBEDDING_ERRORS", errors)
    monkeypatch.setattr("Medical_KG.embeddings.metrics.EMBEDDING_LATENCY", latency)
    monkeypatch.setattr("Medical_KG.embeddings.service.EMBEDDING_REQUESTS", requests)
    monkeypatch.setattr("Medical_KG.embeddings.service.EMBEDDING_ERRORS", errors)
    monkeypatch.setattr("Medical_KG.embeddings.service.EMBEDDING_LATENCY", latency)
    return {"requests": requests, "errors": errors, "latency": latency}
