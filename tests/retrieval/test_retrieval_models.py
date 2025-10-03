from __future__ import annotations

from Medical_KG.retrieval.models import (
    RetrievalRequest,
    RetrievalResult,
    RetrieverScores,
    merge_metadata,
    normalize_filters,
)


def test_retriever_scores_as_dict_and_clone() -> None:
    scores = RetrieverScores(bm25=1.2, splade=0.5, dense=0.3, fused=0.8, rerank=0.7)
    assert scores.as_dict() == {
        "bm25": 1.2,
        "splade": 0.5,
        "dense": 0.3,
        "fused": 0.8,
        "rerank": 0.7,
    }
    result = RetrievalResult(
        chunk_id="chunk-1",
        doc_id="doc-1",
        text="snippet",
        title_path=None,
        section=None,
        score=1.0,
        scores=scores,
        metadata={"source": "bm25"},
    )
    updated = result.clone_with_score(2.0, rerank=1.5)
    assert updated.score == 2.0
    assert updated.scores.rerank == 1.5
    assert updated.metadata["source"] == "bm25"


def test_merge_metadata_and_normalize_filters() -> None:
    merged = merge_metadata({"a": 1, "b": None}, {"b": 2, "c": 3})
    assert merged == {"a": 1, "b": 2, "c": 3}
    normalized = normalize_filters({"facet": "drug", "unused": None})
    assert normalized == {"facet": "drug"}
    assert normalize_filters(None) == {}


def test_retrieval_request_defaults() -> None:
    request = RetrievalRequest(query="term")
    assert request.top_k == 20
    assert request.filters == {}
    assert request.rerank_enabled is None
