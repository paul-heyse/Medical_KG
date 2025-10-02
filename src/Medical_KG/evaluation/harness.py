"""Evaluation harness implementing quality checks."""
from __future__ import annotations

from dataclasses import dataclass
from statistics import mean
from typing import Iterable, Mapping, MutableMapping, Sequence

from .metrics import (
    RetrievalMetrics,
    compute_retrieval_metrics,
    drift_delta,
    extraction_f1,
    hallucination_rate,
)
from .models import EvaluationReport, GoldSample, Prediction


@dataclass(slots=True)
class EvaluationSettings:
    recall_threshold: float = 0.8
    ndcg_threshold: float = 0.7
    hallucination_threshold: float = 0.05


class EvaluationHarness:
    """Coordinates computation of retrieval, extraction, and RAG metrics."""

    def __init__(self, settings: EvaluationSettings | None = None) -> None:
        self._settings = settings or EvaluationSettings()

    def evaluate_retrieval(self, gold: Sequence[GoldSample], predictions: Sequence[Prediction]) -> RetrievalMetrics:
        metrics: list[RetrievalMetrics] = []
        prediction_by_id = {pred.query_id: pred for pred in predictions}
        for sample in gold:
            pred = prediction_by_id.get(sample.query_id)
            ranked_ids = pred.ranked_ids if pred else []
            metrics.append(compute_retrieval_metrics(sample.relevant_ids, ranked_ids))
        avg_recall = mean(metric.recall_at_10 for metric in metrics) if metrics else 0.0
        avg_ndcg = mean(metric.ndcg_at_10 for metric in metrics) if metrics else 0.0
        avg_mrr = mean(metric.mrr for metric in metrics) if metrics else 0.0
        return RetrievalMetrics(recall_at_10=avg_recall, ndcg_at_10=avg_ndcg, mrr=avg_mrr)

    def evaluate_extraction(self, gold_spans: Sequence[Sequence[str]], predicted_spans: Sequence[Sequence[str]]) -> Mapping[str, float]:
        scores = [extraction_f1(truth, pred) for truth, pred in zip(gold_spans, predicted_spans)]
        return {
            "f1": mean(scores) if scores else 0.0,
            "min": min(scores) if scores else 0.0,
        }

    def evaluate_rag(self, answers: Sequence[Prediction]) -> Mapping[str, float]:
        claims = [
            {"citations": list(answer.citations)}
            for answer in answers
        ]
        return {
            "hallucination_rate": hallucination_rate(claims),
        }

    def detect_drift(self, current: Mapping[str, float], previous: Mapping[str, float]) -> Mapping[str, float]:
        return drift_delta(current, previous)

    def run(self, gold: Sequence[GoldSample], predictions: Sequence[Prediction]) -> EvaluationReport:
        retrieval = self.evaluate_retrieval(gold, predictions)
        extraction = self.evaluate_extraction(
            [sample.relevant_ids for sample in gold],
            [prediction.ranked_ids[: len(sample.relevant_ids)] for sample, prediction in zip(gold, predictions)],
        )
        rag = self.evaluate_rag(predictions)
        drift = self.detect_drift(
            {"recall_at_10": retrieval.recall_at_10, "ndcg_at_10": retrieval.ndcg_at_10},
            {"recall_at_10": self._settings.recall_threshold, "ndcg_at_10": self._settings.ndcg_threshold},
        )
        report = EvaluationReport(
            retrieval={
                "recall_at_10": retrieval.recall_at_10,
                "ndcg_at_10": retrieval.ndcg_at_10,
                "mrr": retrieval.mrr,
            },
            extraction=dict(extraction),
            rag=dict(rag),
            drift=dict(drift),
        )
        return report

    def smoke_check(self, report: EvaluationReport) -> list[str]:
        failures: list[str] = []
        if report.retrieval["recall_at_10"] < self._settings.recall_threshold:
            failures.append("Recall below threshold")
        if report.retrieval["ndcg_at_10"] < self._settings.ndcg_threshold:
            failures.append("nDCG below threshold")
        if report.rag["hallucination_rate"] > self._settings.hallucination_threshold:
            failures.append("Hallucination rate too high")
        return failures


__all__ = ["EvaluationHarness", "EvaluationSettings"]
