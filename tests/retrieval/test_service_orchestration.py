from __future__ import annotations

import asyncio
import re
from dataclasses import replace

import pytest

from Medical_KG.retrieval.models import RetrievalRequest, RetrievalResult
from Medical_KG.retrieval.service import RetrievalService, RetrieverConfig
from Medical_KG.retrieval.intent import IntentRule

from conftest import (
    FakeOpenSearchClient,
    FakeQwenEmbedder,
    FakeSpladeEncoder,
    FakeVectorClient,
)


class FakeReranker:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str]]] = []

    async def rerank(self, query: str, candidates: list[RetrievalResult]) -> list[RetrievalResult]:
        self.calls.append((query, [candidate.chunk_id for candidate in candidates]))
        if not candidates:
            return candidates
        top = candidates[0].clone_with_score(candidates[0].score + 0.5, rerank=candidates[0].score + 0.5)
        return [top, *candidates[1:]]


class StubOntology:
    def __init__(self, expansions: dict[str, dict[str, float]] | None = None) -> None:
        self._expansions = expansions or {}
        self.calls: list[str] = []

    def expand(self, query: str) -> dict[str, float]:
        self.calls.append(query)
        return dict(self._expansions.get(query, {}))


@pytest.fixture
def retrieval_rules() -> list[IntentRule]:
    return [
        IntentRule(
            name="general",
            keywords=(re.compile(r".*"),),
            boosts={"title_path": 2.0, "facet_json": 1.6, "table_lines": 1.2, "body": 1.0},
            filters={},
        )
    ]


@pytest.fixture
def retrieval_config(fake_opensearch_client: FakeOpenSearchClient) -> RetrieverConfig:
    return RetrieverConfig(
        bm25_index="bm25-index",
        splade_index="splade-index",
        dense_index="dense-index",
        max_top_k=50,
        default_top_k=5,
        rrf_k=60,
        rerank_top_n=3,
        weights={"bm25": 0.5, "splade": 0.3, "dense": 0.2},
        neighbor_merge={"min_cosine": 0.85, "max_tokens": 2000},
        query_cache_seconds=5,
        embedding_cache_seconds=5,
        expansion_cache_seconds=5,
        slo_ms=1500.0,
        multi_granularity={"enabled": True, "indexes": {"chunk": "bm25-index", "graph": "graph-index"}},
    )


@pytest.fixture
def retrieval_service(
    fake_opensearch_client: FakeOpenSearchClient,
    fake_vector_client: FakeVectorClient,
    fake_query_embedder: FakeQwenEmbedder,
    fake_splade_encoder: FakeSpladeEncoder,
    retrieval_rules: list[IntentRule],
    retrieval_config: RetrieverConfig,
) -> RetrievalService:
    ontology = StubOntology({"pembrolizumab": {"keytruda": 1.0}})
    service = RetrievalService(
        opensearch=fake_opensearch_client,
        vector=fake_vector_client,
        embedder=fake_query_embedder,
        splade=fake_splade_encoder,
        intents=retrieval_rules,
        config=retrieval_config,
        reranker=FakeReranker(),
        ontology=ontology,
    )
    return service


@pytest.mark.asyncio
async def test_semantic_retrieval_invokes_vector_search(
    retrieval_service: RetrievalService,
    fake_vector_client: FakeVectorClient,
    fake_query_embedder: FakeQwenEmbedder,
) -> None:
    request = RetrievalRequest(query="pembrolizumab", top_k=4)
    response = await retrieval_service.retrieve(request)
    assert fake_vector_client.queries, "vector search should be executed"
    assert fake_query_embedder.calls == ["pembrolizumab"]
    dense_ids = {result.chunk_id for result in response.results if result.scores.dense is not None}
    assert "chunk-dense-1" in dense_ids


@pytest.mark.asyncio
async def test_sparse_retrieval_uses_splade(
    retrieval_service: RetrievalService,
    fake_opensearch_client: FakeOpenSearchClient,
    fake_splade_encoder: FakeSpladeEncoder,
) -> None:
    request = RetrievalRequest(query="pembrolizumab", top_k=3)
    await retrieval_service.retrieve(request)
    assert fake_splade_encoder.calls == ["pembrolizumab"]
    assert any(index == "splade-index" for index, _ in fake_opensearch_client.executed)


@pytest.mark.asyncio
async def test_graph_results_merge_into_response(
    retrieval_service: RetrievalService,
) -> None:
    request = RetrievalRequest(query="pembrolizumab", top_k=5)
    response = await retrieval_service.retrieve(request)
    chunk_ids = {result.chunk_id for result in response.results}
    assert "chunk-graph-1" in chunk_ids
    graph = next(result for result in response.results if result.chunk_id == "chunk-graph-1")
    assert graph.metadata.get("granularity") == "graph"


@pytest.mark.asyncio
async def test_hybrid_fusion_falls_back_to_rrf(
    fake_opensearch_hits: dict[str, list[dict[str, object]]],
    fake_vector_client: FakeVectorClient,
    fake_query_embedder: FakeQwenEmbedder,
    fake_splade_encoder: FakeSpladeEncoder,
    retrieval_rules: list[IntentRule],
) -> None:
    zero_weight_config = RetrieverConfig(
        bm25_index="bm25-index",
        splade_index="splade-index",
        dense_index="dense-index",
        max_top_k=20,
        default_top_k=5,
        rrf_k=10,
        rerank_top_n=2,
        weights={"bm25": 0.0, "splade": 0.0, "dense": 0.0},
        neighbor_merge={"min_cosine": 0.0, "max_tokens": 2000},
        query_cache_seconds=1,
        embedding_cache_seconds=1,
        expansion_cache_seconds=1,
        slo_ms=1500.0,
        multi_granularity={"enabled": False, "indexes": {}},
    )
    opensearch = FakeOpenSearchClient(hits_by_index=fake_opensearch_hits)
    service = RetrievalService(
        opensearch=opensearch,
        vector=fake_vector_client,
        embedder=fake_query_embedder,
        splade=fake_splade_encoder,
        intents=retrieval_rules,
        config=zero_weight_config,
        reranker=None,
        ontology=StubOntology(),
    )
    response = await service.retrieve(RetrievalRequest(query="pembrolizumab"))
    assert response.results, "RRF fallback should yield results"
    assert all(result.scores.fused is not None for result in response.results)


@pytest.mark.asyncio
async def test_rank_normalization_and_deduplication(
    fake_vector_client: FakeVectorClient,
    fake_query_embedder: FakeQwenEmbedder,
    fake_splade_encoder: FakeSpladeEncoder,
    retrieval_rules: list[IntentRule],
) -> None:
    duplicate_hits = {
        "bm25-index": [
            {
                "chunk_id": "shared-chunk",
                "doc_id": "doc-a",
                "text": "Primary chunk",
                "score": 1.0,
                "metadata": {"cosine": 0.95},
            }
        ],
        "splade-index": [
            {
                "chunk_id": "shared-chunk",
                "doc_id": "doc-a",
                "text": "Primary chunk",
                "score": 0.4,
                "metadata": {},
            }
        ],
    }
    config = RetrieverConfig(
        bm25_index="bm25-index",
        splade_index="splade-index",
        dense_index="dense-index",
        max_top_k=10,
        default_top_k=5,
        rrf_k=60,
        rerank_top_n=2,
        weights={"bm25": 0.7, "splade": 0.3, "dense": 0.0},
        neighbor_merge={"min_cosine": 0.0, "max_tokens": 2000},
        query_cache_seconds=1,
        embedding_cache_seconds=1,
        expansion_cache_seconds=1,
        slo_ms=1500.0,
        multi_granularity={"enabled": False, "indexes": {}},
    )
    service = RetrievalService(
        opensearch=FakeOpenSearchClient(hits_by_index=duplicate_hits),
        vector=fake_vector_client,
        embedder=fake_query_embedder,
        splade=fake_splade_encoder,
        intents=retrieval_rules,
        config=config,
        reranker=None,
        ontology=StubOntology(),
    )
    response = await service.retrieve(RetrievalRequest(query="pembrolizumab"))
    shared = [result for result in response.results if result.chunk_id == "shared-chunk"]
    assert len(shared) == 1
    result = shared[0]
    assert result.scores.bm25 == pytest.approx(1.0)
    assert result.scores.fused is not None
