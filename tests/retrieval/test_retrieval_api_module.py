from __future__ import annotations

from typing import cast

import httpx
import pytest
from fastapi import FastAPI

from Medical_KG.retrieval.api import create_router
from Medical_KG.retrieval.models import RetrievalRequest, RetrievalResponse, RetrievalResult, RetrieverScores, RetrieverTiming
from Medical_KG.retrieval.service import RetrievalService


class StubRetrievalService:
    async def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        result = RetrievalResult(
            chunk_id="chunk-1",
            doc_id="doc-1",
            text="result",
            title_path=None,
            section=None,
            score=1.2,
            scores=RetrieverScores(bm25=1.0, fused=1.2),
            start=10,
            end=20,
            metadata={"foo": "bar"},
        )
        return RetrievalResponse(
            results=[result],
            timings=[RetrieverTiming(component="bm25", duration_ms=12.0)],
            expanded_terms={"term": 1.0},
            intent=request.intent or "general",
            latency_ms=25.0,
            from_=request.from_,
            size=1,
            metadata={"feature_flags": {"rerank_enabled": True}},
        )


@pytest.mark.asyncio
async def test_retrieval_api_transforms_response() -> None:
    app = FastAPI()
    router = create_router(cast(RetrievalService, StubRetrievalService()))
    app.include_router(router)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        payload = {
            "query": "pembrolizumab",
            "topK": 5,
            "from": 2,
            "filters": {"facet": "drug"},
            "explain": True,
        }
        response = await client.post("/retrieve", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["results"][0]["metadata"]["foo"] == "bar"
    assert body["query_meta"]["feature_flags"]["rerank_enabled"] is True
    assert body["query_meta"]["expanded_terms"] == {"term": 1.0}
