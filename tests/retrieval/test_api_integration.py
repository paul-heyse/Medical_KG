from __future__ import annotations

import json
from dataclasses import dataclass
from typing import AsyncIterator, cast

import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI

from Medical_KG.retrieval.api import create_router
from Medical_KG.retrieval.models import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    RetrieverScores,
    RetrieverTiming,
)
from Medical_KG.retrieval.service import RetrievalService


@dataclass
class DummyRetrievalService:
    calls: list[RetrievalRequest]

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        self.calls.append(request)
        result = RetrievalResult(
            chunk_id="chunk-1",
            doc_id="doc-1",
            text="Pembrolizumab overview",
            title_path=None,
            section=None,
            score=1.0,
            scores=RetrieverScores(bm25=1.0, fused=1.0),
            metadata={"foo": "bar"},
        )
        return RetrievalResponse(
            results=[result],
            timings=[RetrieverTiming(component="bm25", duration_ms=12.0)],
            expanded_terms={"pembrolizumab": 1.0},
            intent=request.intent or "general",
            latency_ms=25.0,
            from_=request.from_,
            size=1,
            metadata={"feature_flags": {"rerank_enabled": True}},
        )


@pytest_asyncio.fixture
async def api_client() -> AsyncIterator[tuple[httpx.AsyncClient, DummyRetrievalService]]:
    service = DummyRetrievalService(calls=[])
    app = FastAPI()
    router = create_router(cast(RetrievalService, service))
    app.include_router(router)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, service


@pytest.mark.asyncio
async def test_retrieve_endpoint_success(
    api_client: tuple[httpx.AsyncClient, DummyRetrievalService],
) -> None:
    client, service = api_client
    payload = {"query": "Pembrolizumab", "topK": 2}
    response = await client.post("/retrieve", json=payload)
    assert response.status_code == 200
    assert service.calls[0].query == "Pembrolizumab"
    body = response.json()
    assert body["results"][0]["chunk_id"] == "chunk-1"
    assert body["query_meta"]["intent_detected"] == "general"


@pytest.mark.asyncio
async def test_retrieve_endpoint_streaming(
    api_client: tuple[httpx.AsyncClient, DummyRetrievalService],
) -> None:
    client, _ = api_client
    payload = {"query": "Pembrolizumab"}
    async with client.stream("POST", "/retrieve", json=payload) as response:
        assert response.status_code == 200
        body = json.loads(await response.aread())
    assert body["results"][0]["metadata"]["foo"] == "bar"
