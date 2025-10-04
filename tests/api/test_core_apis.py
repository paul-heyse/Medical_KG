from __future__ import annotations

import asyncio
import os
from typing import Any, Protocol, cast

import pytest

from Medical_KG.api.auth import Authenticator
from Medical_KG.app import create_app
from Medical_KG.config.manager import SecretResolver
from Medical_KG.services.chunks import Chunk
from Medical_KG.utils.optional_dependencies import HttpxModule, get_httpx_module


class FastAPI(Protocol):  # pragma: no cover - minimal contract for typing
    state: Any


HTTPX: HttpxModule = get_httpx_module()
ASGITransport = HTTPX.ASGITransport


@pytest.fixture
def app(monkeypatch: pytest.MonkeyPatch) -> FastAPI:
    monkeypatch.setenv("NCBI_API_KEY", "test-key")
    monkeypatch.setenv("PMC_API_KEY", "test-key")
    monkeypatch.setenv("CTGOV_SANDBOX_KEY", "test-key")
    monkeypatch.setenv("OPEN_FDA_SANDBOX_KEY", "test-key")

    def _build_authenticator() -> Authenticator:
        return Authenticator(
            valid_api_keys={
                "demo-key": {
                    "retrieve:read",
                    "facets:write",
                    "extract:write",
                    "kg:write",
                }
            }
        )

    monkeypatch.setattr(
        "Medical_KG.api.routes.build_default_authenticator",
        _build_authenticator,
    )

    def _resolve(self: SecretResolver, key: str, default: str | None = None) -> str:
        if key in os.environ:
            return os.environ[key]
        if default is not None:
            return default
        return "test-secret"

    monkeypatch.setattr(SecretResolver, "resolve", _resolve)
    application = cast(FastAPI, create_app())
    router = application.state.api_router
    router.chunk_repository.add(
        Chunk(
            chunk_id="chunk-1",
            doc_id="doc-1",
            text=(
                "Patients receiving the treatment arm had a hazard ratio 0.68 (0.52-0.88, p=0.01). "
                "Grade 3 nausea occurred in 12/100 participants taking Enalapril 10mg PO BID."
            ),
            section="results",
        )
    )
    return application


def test_generate_facets_and_get_chunk(app: FastAPI) -> None:
    headers: dict[str, str] = {
        "X-API-Key": "demo-key",
        "X-License-Tier": "public",
        "traceparent": "00-{}-{}-01".format("a" * 32, "b" * 16),
    }

    async def run() -> None:
        async with HTTPX.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/facets/generate", json={"chunk_ids": ["chunk-1"]}, headers=headers
            )
            assert response.status_code == 200
            facets = response.json()["facets_by_chunk"]["chunk-1"]
            assert any(facet["type"] == "pico" for facet in facets)

            chunk_response = await client.get("/chunks/chunk-1", headers=headers)
            assert chunk_response.status_code == 200
            payload = chunk_response.json()
            for facet in payload["facets"]:
                if facet["type"] == "ae":
                    assert facet.get("meddra_pt") is None
            assert "x-request-id" in chunk_response.headers
            assert chunk_response.headers.get("traceparent") == headers["traceparent"]

    asyncio.run(run())


def test_idempotency_replay_and_conflict(app: FastAPI) -> None:
    headers: dict[str, str] = {
        "X-API-Key": "demo-key",
        "Idempotency-Key": "123e4567-e89b-12d3-a456-426614174000",
    }
    payload: dict[str, object] = {"chunk_ids": ["chunk-1"]}

    async def run() -> None:
        async with HTTPX.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            first = await client.post("/facets/generate", json=payload, headers=headers)
            assert first.status_code == 200
            replay = await client.post("/facets/generate", json=payload, headers=headers)
            assert replay.status_code == 200
            assert replay.json() == first.json()

            conflict = await client.post(
                "/facets/generate",
                json={"chunk_ids": ["missing"]},
                headers=headers,
            )
            assert conflict.status_code == 409

    asyncio.run(run())


def test_rate_limiting_and_retrieval_headers(app: FastAPI) -> None:
    headers: dict[str, str] = {"X-API-Key": "demo-key"}

    async def run() -> None:
        async with HTTPX.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            await client.post("/facets/generate", json={"chunk_ids": ["chunk-1"]}, headers=headers)
            response = await client.get("/chunks/chunk-1", headers=headers)
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
            assert "X-RateLimit-Reset" in response.headers

            retrieval = await client.post(
                "/retrieve",
                json={"query": "hazard ratio", "filters": {"facet_type": "endpoint"}},
                headers=headers,
            )
            assert retrieval.status_code == 200
            body = retrieval.json()
            assert body["results"]

    asyncio.run(run())


def test_kg_write_happy_path_and_validation_error(app: FastAPI) -> None:
    headers: dict[str, str] = {"X-API-Key": "demo-key"}
    valid_payload = {
        "nodes": [
            {
                "id": "outcome-1",
                "label": "Outcome",
                "unit_ucum": "1",
                "loinc": "LP12345-6",
            },
            {
                "id": "evidence-1",
                "label": "Evidence",
                "unit_ucum": "1",
                "outcome_loinc": "LP12345-6",
                "provenance": ["doc-1"],
                "spans": [{"start": 10, "end": 20}],
                "outcome": {
                    "id": "outcome-1",
                    "loinc": "LP12345-6",
                },
            },
        ],
        "relationships": [{"type": "MEASURES", "start_id": "evidence-1", "end_id": "outcome-1"}],
    }
    invalid_payload: dict[str, object] = {
        "nodes": [
            {
                "id": "bad-evidence",
                "label": "Evidence",
                "unit_ucum": "1",
                "outcome_loinc": "LP00000-0",
            }
        ],
        "relationships": [],
    }

    async def run() -> None:
        async with HTTPX.AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            success = await client.post("/kg/write", json=valid_payload, headers=headers)
            assert success.status_code == 200
            body = success.json()
            assert body["written_nodes"] == 2
            assert body["written_relationships"] == 1

            failure = await client.post("/kg/write", json=invalid_payload, headers=headers)
            assert failure.status_code == 422
            error = failure.json()["detail"]
            assert error["code"] == "kg_validation_failed"
            assert error["issues"]

    asyncio.run(run())
