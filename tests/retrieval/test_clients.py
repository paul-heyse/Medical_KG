from __future__ import annotations

from Medical_KG.retrieval.clients import (
    ConstantEmbeddingClient,
    InMemorySearch,
    InMemorySearchHit,
    InMemoryVector,
    PassthroughEncoder,
)


def test_inmemory_search_hit_to_result() -> None:
    hit = InMemorySearchHit(
        chunk_id="chunk-1",
        doc_id="doc-1",
        text="snippet",
        score=2.5,
        metadata={"source": "bm25"},
    )
    result = hit.to_result(source="bm25")
    assert result.chunk_id == "chunk-1"
    assert result.scores.bm25 == 2.5
    assert result.metadata["source"] == "bm25"


def test_inmemory_search_and_vector_clients() -> None:
    hits = [
        InMemorySearchHit(chunk_id="chunk-1", doc_id="doc-1", text="A", score=1.0),
        InMemorySearchHit(chunk_id="chunk-2", doc_id="doc-2", text="B", score=0.5),
    ]
    search = InMemorySearch(hits)
    vector = InMemoryVector(hits)
    search_hits = search.search(index="test", body={}, size=1)
    vector_hits = vector.query(index="vec", embedding=[0.1, 0.2], top_k=1)
    assert search_hits[0]["chunk_id"] == "chunk-1"
    assert vector_hits[0]["doc_id"] == "doc-1"


def test_passthrough_encoder_and_constant_embedding() -> None:
    encoder = PassthroughEncoder({"term": {"term": 1.5}})
    embedding_client = ConstantEmbeddingClient([0.4, 0.5, 0.6])
    assert encoder.expand("term") == {"term": 1.5}
    assert encoder.expand("unknown") == {}
    assert list(embedding_client.embed("text")) == [0.4, 0.5, 0.6]
