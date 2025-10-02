from __future__ import annotations

import asyncio
import re

from Medical_KG.retrieval import (
    ConceptCatalogClient,
    ConstantEmbeddingClient,
    IntentRule,
    InMemorySearch,
    InMemorySearchHit,
    InMemoryVector,
    OntologyExpander,
    OntologyTerm,
    PassthroughEncoder,
    RetrievalService,
    RetrieverConfig,
    RetrievalRequest,
)


class StubCatalog(ConceptCatalogClient):
    def synonyms(self, identifier: str):  # pragma: no cover - used in tests
        if identifier.lower().startswith("nct"):
            yield OntologyTerm(term=identifier.upper(), weight=1.0)

    def search(self, text: str):  # pragma: no cover - used in tests
        if len(text) > 2:
            yield OntologyTerm(term=f"{text}_syn", weight=0.8)


def _service() -> RetrievalService:
    hits = [
        InMemorySearchHit(
            chunk_id="chunk-1",
            doc_id="doc-1",
            text="Sacubitril overview",
            title_path="Study/Overview",
            score=1.2,
            metadata={"cosine": 0.91},
        ),
        InMemorySearchHit(
            chunk_id="chunk-2",
            doc_id="doc-2",
            text="Valsartan outcomes",
            title_path="Study/Endpoints",
            score=0.9,
            metadata={"cosine": 0.89},
        ),
    ]
    opensearch = InMemorySearch(hits)
    vector = InMemoryVector(hits)
    encoder = PassthroughEncoder({"heart failure": {"heart": 0.9, "failure": 0.8}})
    config = RetrieverConfig(
        bm25_index="chunks_v1",
        splade_index="chunks_v1",
        dense_index="chunk_qwen_idx",
        max_top_k=50,
        default_top_k=10,
        rrf_k=60,
        rerank_top_n=5,
        weights={"bm25": 0.5, "splade": 0.3, "dense": 0.2},
        neighbor_merge={"min_cosine": 0.8, "max_tokens": 4000},
        query_cache_seconds=60,
        embedding_cache_seconds=60,
        expansion_cache_seconds=60,
        slo_ms=1500.0,
        multi_granularity={"enabled": True, "indexes": {"chunk": "chunks_v1"}},
    )
    rules = [
        IntentRule(
            name="general",
            keywords=(re.compile(r".*"),),
            boosts={"title_path": 2.0, "facet_json": 1.6, "table_lines": 1.2, "body": 1.0},
            filters={},
        )
    ]
    service = RetrievalService(
        opensearch=opensearch,
        vector=vector,
        embedder=ConstantEmbeddingClient([0.5, 0.4, 0.3]),
        splade=encoder,
        intents=rules,
        config=config,
        ontology=OntologyExpander(StubCatalog()),
    )
    return service


def test_retrieval_service_combines_scores() -> None:
    service = _service()
    request = RetrievalRequest(query="heart failure", top_k=5)
    response = asyncio.run(service.retrieve(request))
    assert response.results, "Expected fused results"
    first = response.results[0]
    assert first.scores.fused is not None
    assert response.intent == "general"
    assert response.expanded_terms
    assert response.metadata["feature_flags"]["rerank_enabled"] is False
