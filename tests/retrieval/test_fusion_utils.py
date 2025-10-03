from __future__ import annotations

import pytest

from Medical_KG.retrieval.fusion import min_max_normalize, reciprocal_rank_fusion, weighted_fusion
from Medical_KG.retrieval.models import RetrievalResult, RetrieverScores


def _result(chunk_id: str, score: float) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        doc_id=f"doc-{chunk_id}",
        text="",
        title_path=None,
        section=None,
        score=score,
        scores=RetrieverScores(bm25=score),
    )


def test_min_max_normalize_handles_constant_scores() -> None:
    results = [_result("a", 1.0), _result("b", 1.0)]
    assert min_max_normalize(results) == {"a": 1.0, "b": 1.0}


def test_weighted_fusion_applies_weights() -> None:
    pools = {"bm25": [_result("a", 2.0)], "splade": [_result("a", 1.0)]}
    scores = weighted_fusion(pools, {"bm25": 0.6, "splade": 0.4})
    assert scores["a"] == pytest.approx(1.0)


def test_weighted_fusion_empty_triggers_rrf_fallback() -> None:
    fused = weighted_fusion({"bm25": [], "splade": []}, {"bm25": 1.0})
    assert fused == {}


def test_reciprocal_rank_fusion_orders_results() -> None:
    pool = {
        "bm25": [_result("a", 2.0), _result("b", 1.5)],
        "dense": [_result("b", 0.9)],
    }
    fused = reciprocal_rank_fusion(pool, k=50)
    assert fused["b"] > fused["a"]
