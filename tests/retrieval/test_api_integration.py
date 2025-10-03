from __future__ import annotations

from dataclasses import dataclass
import json

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from fastapi.security import HTTPAuthorizationCredentials

from Medical_KG.api.auth import Authenticator, Principal
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
    class ExpiringAuthenticator(Authenticator):
        def authenticate(
            self,
            credentials: HTTPAuthorizationCredentials | None,
            api_key: str | None,
        ) -> Principal:
            if credentials is not None and credentials.credentials == "expired-token":
                raise HTTPException(status_code=401, detail="Token expired")
            return super().authenticate(credentials, api_key)

    authenticator = ExpiringAuthenticator(
        valid_api_keys={"valid-key": {"retrieve:read"}, "no-scope": {"facets:write"}}
    )
    retrieval_service = DummyRetrievalService()
    router = ApiRouter(authenticator=authenticator, retrieval_service=retrieval_service)
    app = FastAPI()
    app.include_router(router)
    return TestClient(app), retrieval_service


def _bearer_headers() -> dict[str, str]:
    return {"Authorization": "Bearer super-secret"}


def _expired_headers() -> dict[str, str]:
    return {"Authorization": "Bearer expired-token"}


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


def test_retrieve_endpoint_expired_token(api_client: tuple[TestClient, DummyRetrievalService]) -> None:
    client, _ = api_client
    response = client.post("/retrieve", json={"query": "Pembrolizumab"}, headers=_expired_headers())
    assert response.status_code == 401
    assert response.json()["detail"] == "Token expired"


def test_retrieve_endpoint_streaming(api_client: tuple[TestClient, DummyRetrievalService]) -> None:
    client, _ = api_client
    payload = {"query": "Pembrolizumab"}
    with client.stream("POST", "/retrieve", json=payload, headers=_bearer_headers()) as response:
        assert response.status_code == 200
        body = b"".join(response.iter_bytes())
    data = json.loads(body)
    assert data["results"][0]["chunk_id"] == "chunk-1"
