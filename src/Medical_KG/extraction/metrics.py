"""Simple evaluation metrics for clinical extraction outputs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from .models import ExtractionBase, ExtractionType


@dataclass(slots=True)
class ExtractionMetrics:
    pico_completeness: float
    effect_f1_relaxed: float
    ae_accuracy: float
    dose_ucum_accuracy: float
    eligibility_logic_accuracy: float


class ExtractionEvaluator:
    """Compute aggregate metrics against gold annotations."""

    def evaluate(
        self, predictions: Sequence[ExtractionBase], gold: Sequence[ExtractionBase]
    ) -> ExtractionMetrics:
        gold_by_type = self._group_by_type(gold)
        pred_by_type = self._group_by_type(predictions)

        pico_completeness = self._pico_completeness(pred_by_type.get(ExtractionType.PICO, []))
        effect_f1 = self._effect_f1(
            pred_by_type.get(ExtractionType.EFFECT, []), gold_by_type.get(ExtractionType.EFFECT, [])
        )
        ae_accuracy = self._ae_accuracy(
            pred_by_type.get(ExtractionType.ADVERSE_EVENT, []),
            gold_by_type.get(ExtractionType.ADVERSE_EVENT, []),
        )
        dose_accuracy = self._dose_accuracy(pred_by_type.get(ExtractionType.DOSE, []))
        eligibility_accuracy = self._eligibility_accuracy(
            pred_by_type.get(ExtractionType.ELIGIBILITY, []),
            gold_by_type.get(ExtractionType.ELIGIBILITY, []),
        )

        return ExtractionMetrics(
            pico_completeness=pico_completeness,
            effect_f1_relaxed=effect_f1,
            ae_accuracy=ae_accuracy,
            dose_ucum_accuracy=dose_accuracy,
            eligibility_logic_accuracy=eligibility_accuracy,
        )

    def _group_by_type(
        self, extractions: Iterable[ExtractionBase]
    ) -> dict[ExtractionType, list[ExtractionBase]]:
        grouped: dict[ExtractionType, list[ExtractionBase]] = {}
        for extraction in extractions:
            grouped.setdefault(extraction.type, []).append(extraction)
        return grouped

    def _pico_completeness(self, extractions: Sequence[ExtractionBase]) -> float:
        if not extractions:
            return 0.0
        complete = 0
        for extraction in extractions:
            pico = extraction
            if pico.population and pico.interventions and pico.outcomes:
                complete += 1
        return complete / len(extractions)

    def _effect_f1(
        self, predictions: Sequence[ExtractionBase], gold: Sequence[ExtractionBase]
    ) -> float:
        if not predictions or not gold:
            return 0.0
        matches = 0
        for pred in predictions:
            for target in gold:
                if (
                    pred.measure_type == target.measure_type
                    and abs(pred.value - target.value) <= 0.01
                    and (
                        pred.ci_low is None
                        or target.ci_low is None
                        or abs(pred.ci_low - target.ci_low) <= 0.01
                    )
                    and (
                        pred.ci_high is None
                        or target.ci_high is None
                        or abs(pred.ci_high - target.ci_high) <= 0.01
                    )
                ):
                    matches += 1
                    break
        precision = matches / len(predictions)
        recall = matches / len(gold)
        if precision + recall == 0:
            return 0.0
        return 2 * precision * recall / (precision + recall)

    def _ae_accuracy(
        self, predictions: Sequence[ExtractionBase], gold: Sequence[ExtractionBase]
    ) -> float:
        if not predictions or not gold:
            return 0.0
        total = min(len(predictions), len(gold))
        correct = 0
        for pred, target in zip(predictions, gold):
            if pred.term.lower() == target.term.lower() and pred.grade == target.grade:
                correct += 1
        return correct / total

    def _dose_accuracy(self, predictions: Sequence[ExtractionBase]) -> float:
        if not predictions:
            return 0.0
        correct = 0
        for pred in predictions:
            if pred.unit and pred.unit.isupper():
                correct += 1
        return correct / len(predictions)

    def _eligibility_accuracy(
        self,
        predictions: Sequence[ExtractionBase],
        gold: Sequence[ExtractionBase],
    ) -> float:
        if not predictions or not gold:
            return 0.0
        total = min(len(predictions), len(gold))
        correct = 0
        for pred, target in zip(predictions, gold):
            pred_logic = pred.criteria[0].logic if pred.criteria else None
            target_logic = target.criteria[0].logic if target.criteria else None
            if not pred_logic or not target_logic:
                continue
            if pred_logic.age == target_logic.age:
                correct += 1
        return correct / total


__all__ = ["ExtractionEvaluator", "ExtractionMetrics"]
