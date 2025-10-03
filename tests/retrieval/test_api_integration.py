from __future__ import annotations

from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from Medical_KG.api.auth import Authenticator
from Medical_KG.api.routes import ApiRouter
from Medical_KG.services.retrieval import RetrievalResult as LegacyRetrievalResult, RetrievalService as LegacyService


@dataclass
class DummyRetrievalService(LegacyService):
    calls: list[tuple[str, str | None, int]]

    def __init__(self) -> None:
        super().__init__()
        self.calls = []

    def search(self, query: str, *, facet_type: str | None = None, top_k: int = 5):  # type: ignore[override]
        self.calls.append((query, facet_type, top_k))
        return [
            LegacyRetrievalResult(
                chunk_id="chunk-1",
                score=1.0,
                facet_types=[facet_type or "drug"],
                snippet="Pembrolizumab overview",
            )
        ]


@pytest.fixture
def api_client() -> tuple[TestClient, DummyRetrievalService]:
    authenticator = Authenticator(valid_api_keys={"valid-key": {"retrieve:read"}, "no-scope": {"facets:write"}})
    retrieval_service = DummyRetrievalService()
    router = ApiRouter(authenticator=authenticator, retrieval_service=retrieval_service)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app), retrieval_service


def _bearer_headers() -> dict[str, str]:
    return {"Authorization": "Bearer super-secret"}


def test_retrieve_endpoint_success(api_client: tuple[TestClient, DummyRetrievalService]) -> None:
    client, retrieval = api_client
    payload = {"query": "Pembrolizumab", "topK": 2}
    response = client.post("/retrieve", json=payload, headers=_bearer_headers())
    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["chunk_id"] == "chunk-1"
    assert retrieval.calls[0] == ("Pembrolizumab", None, 2)
    assert "X-RateLimit-Limit" in response.headers


def test_retrieve_endpoint_missing_credentials(api_client: tuple[TestClient, DummyRetrievalService]) -> None:
    client, _ = api_client
    response = client.post("/retrieve", json={"query": "test"})
    assert response.status_code == 401


def test_retrieve_endpoint_invalid_api_key(api_client: tuple[TestClient, DummyRetrievalService]) -> None:
    client, _ = api_client
    response = client.post("/retrieve", json={"query": "test"}, headers={"X-API-Key": "bad"})
    assert response.status_code == 401


def test_retrieve_endpoint_scope_enforced(api_client: tuple[TestClient, DummyRetrievalService]) -> None:
    client, _ = api_client
    response = client.post(
        "/retrieve",
        json={"query": "test"},
        headers={"X-API-Key": "no-scope"},
    )
    assert response.status_code == 403


def test_retrieve_endpoint_validation_error(api_client: tuple[TestClient, DummyRetrievalService]) -> None:
    client, _ = api_client
    response = client.post("/retrieve", json={}, headers=_bearer_headers())
    assert response.status_code == 422
