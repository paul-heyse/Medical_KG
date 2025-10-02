from __future__ import annotations

from Medical_KG.evaluation import EvaluationHarness, EvaluationSettings, GoldSample, Prediction


def test_retrieval_metrics_average() -> None:
    gold = [
        GoldSample(query_id="q1", query="q", intent="endpoint", relevant_ids=["d1", "d2"]),
        GoldSample(query_id="q2", query="q", intent="endpoint", relevant_ids=["d3"]),
    ]
    predictions = [
        Prediction(query_id="q1", ranked_ids=["d1", "d4", "d2"], citations=[{"doc_id": "d1"}]),
        Prediction(query_id="q2", ranked_ids=["d5", "d3"], citations=[{"doc_id": "d3"}]),
    ]
    harness = EvaluationHarness()
    report = harness.run(gold, predictions)
    assert report.retrieval["recall_at_10"] > 0.5
    assert not harness.smoke_check(report)


def test_hallucination_detection() -> None:
    gold = [GoldSample(query_id="q1", query="q", intent="endpoint", relevant_ids=["d1"])]
    predictions = [Prediction(query_id="q1", ranked_ids=["d1"], citations=[])]
    harness = EvaluationHarness(EvaluationSettings(hallucination_threshold=0.0))
    report = harness.run(gold, predictions)
    assert harness.smoke_check(report), "Should flag hallucination when citations missing"


