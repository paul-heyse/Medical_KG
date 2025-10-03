from __future__ import annotations

from typing import Mapping, Sequence

import pytest

from Medical_KG.retrieval.caching import TTLCache
from Medical_KG.retrieval.models import RetrievalRequest
from Medical_KG.retrieval.service import RetrievalService, RetrieverConfig
from Medical_KG.retrieval.intent import IntentRule
from Medical_KG.retrieval.ontology import OntologyExpander
from Medical_KG.retrieval.types import SearchHit, VectorHit

from tests.conftest import (
    FakeOpenSearchClient,
    FakeQwenEmbedder,
    FakeSpladeEncoder,
    FakeVectorClient,
)


class CountingOntology(OntologyExpander):
    def __init__(self) -> None:
        super().__init__()
        self.calls: list[str] = []

    def expand(self, query: str) -> dict[str, float]:
        self.calls.append(query)
        return {query: 1.0}


@pytest.fixture
def cache_config() -> RetrieverConfig:
    return RetrieverConfig(
        bm25_index="bm25-index",
        splade_index="splade-index",
        dense_index="dense-index",
        max_top_k=10,
        default_top_k=5,
        rrf_k=10,
        rerank_top_n=2,
        weights={"bm25": 0.6, "splade": 0.2, "dense": 0.2},
        neighbor_merge={"min_cosine": 0.85, "max_tokens": 2000},
        query_cache_seconds=60,
        embedding_cache_seconds=120,
        expansion_cache_seconds=120,
        slo_ms=1500.0,
        multi_granularity={"enabled": False, "indexes": {}},
    )


@pytest.fixture
def cache_rules() -> list[IntentRule]:
    return [IntentRule(name="general", keywords=(), boosts={}, filters={})]


@pytest.fixture
def cache_service(
    fake_opensearch_client: FakeOpenSearchClient,
    fake_vector_client: FakeVectorClient,
    fake_query_embedder: FakeQwenEmbedder,
    fake_splade_encoder: FakeSpladeEncoder,
    cache_rules: list[IntentRule],
    cache_config: RetrieverConfig,
) -> RetrievalService:
    return RetrievalService(
        opensearch=fake_opensearch_client,
        vector=fake_vector_client,
        embedder=fake_query_embedder,
        splade=fake_splade_encoder,
        intents=cache_rules,
        config=cache_config,
        reranker=None,
    )


def test_ttl_cache_basic_cycle() -> None:
    cache: TTLCache[int] = TTLCache(ttl_seconds=10)
    created = cache.get_or_set("key", lambda: 41)
    assert created == 41
    cached = cache.get("key")
    assert cached == 41


def test_ttl_cache_expiration(monkeypatch: pytest.MonkeyPatch) -> None:
    cache: TTLCache[int] = TTLCache(ttl_seconds=0)
    cache.set("key", 99)
    assert cache.get("key") is None


def test_ttl_cache_invalidation() -> None:
    cache: TTLCache[int] = TTLCache(ttl_seconds=10)
    cache.set("key", 77)
    cache.invalidate("key")
    assert cache.get("key") is None


@pytest.mark.asyncio
async def test_query_cache_hits(cache_service: RetrievalService, fake_opensearch_client: FakeOpenSearchClient) -> None:
    request = RetrievalRequest(query="pembrolizumab")
    first = await cache_service.retrieve(request)
    second = await cache_service.retrieve(request)
    assert first.results[0].chunk_id == second.results[0].chunk_id
    assert len(fake_opensearch_client.executed) == 2  # bm25 + splade executed once


@pytest.mark.asyncio
async def test_cache_miss_after_invalidation(cache_service: RetrievalService, fake_opensearch_client: FakeOpenSearchClient) -> None:
    request = RetrievalRequest(query="pembrolizumab")
    await cache_service.retrieve(request)
    key = cache_service._cache_key(request)
    cache_service._query_cache.invalidate(key)
    await cache_service.retrieve(request)
    # 4 calls: initial bm25+splade, second bm25+splade after invalidation
    assert len(fake_opensearch_client.executed) == 4


@pytest.mark.asyncio
async def test_embedding_cache_reuses_vectors(
    fake_opensearch_hits: Mapping[str, Sequence[SearchHit]],
    fake_vector_hits: Sequence[VectorHit],
) -> None:
    embedder = FakeQwenEmbedder({"query": [0.1, 0.2, 0.3]})
    service = RetrievalService(
        opensearch=FakeOpenSearchClient(fake_opensearch_hits),
        vector=FakeVectorClient(fake_vector_hits),
        embedder=embedder,
        splade=FakeSpladeEncoder({}),
        intents=[IntentRule(name="general", keywords=(), boosts={}, filters={})],
        config=RetrieverConfig(
            bm25_index="bm25-index",
            splade_index="splade-index",
            dense_index="dense-index",
            max_top_k=5,
            default_top_k=5,
            rrf_k=60,
            rerank_top_n=2,
            weights={"bm25": 1.0, "splade": 0.0, "dense": 0.0},
            neighbor_merge={"min_cosine": 0.0, "max_tokens": 2000},
            query_cache_seconds=60,
            embedding_cache_seconds=300,
            expansion_cache_seconds=300,
            slo_ms=1500.0,
            multi_granularity={"enabled": False, "indexes": {}},
        ),
        reranker=None,
        ontology=CountingOntology(),
    )
    request = RetrievalRequest(query="query")
    await service.retrieve(request)
    await service.retrieve(request)
    assert embedder.calls == ["query"]


@pytest.mark.asyncio
async def test_expansion_cache_avoids_duplicate_calls(
    fake_opensearch_hits: Mapping[str, Sequence[SearchHit]],
    fake_vector_hits: Sequence[VectorHit],
) -> None:
    ontology = CountingOntology()
    service = RetrievalService(
        opensearch=FakeOpenSearchClient(fake_opensearch_hits),
        vector=FakeVectorClient(fake_vector_hits),
        embedder=FakeQwenEmbedder({"query": [0.1, 0.2, 0.3]}),
        splade=FakeSpladeEncoder({}),
        intents=[IntentRule(name="general", keywords=(), boosts={}, filters={})],
        config=RetrieverConfig(
            bm25_index="bm25-index",
            splade_index="splade-index",
            dense_index="dense-index",
            max_top_k=5,
            default_top_k=5,
            rrf_k=60,
            rerank_top_n=2,
            weights={"bm25": 1.0, "splade": 0.0, "dense": 0.0},
            neighbor_merge={"min_cosine": 0.0, "max_tokens": 2000},
            query_cache_seconds=60,
            embedding_cache_seconds=300,
            expansion_cache_seconds=300,
            slo_ms=1500.0,
            multi_granularity={"enabled": False, "indexes": {}},
        ),
        reranker=None,
        ontology=ontology,
    )
    request = RetrievalRequest(query="query")
    await service.retrieve(request)
    await service.retrieve(request)
    assert ontology.calls == ["query"]
