"""Validation and dead-letter handling for clinical extractions."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List

from Medical_KG.facets.tokenizer import count_tokens

from .models import (
    AdverseEventExtraction,
    DoseExtraction,
    EffectExtraction,
    EligibilityExtraction,
    ExtractionBase,
)


@dataclass(slots=True)
class DeadLetterRecord:
    reason: str
    payload_hash: str
    timestamp: datetime


@dataclass(slots=True)
class DeadLetterQueue:
    records: List[DeadLetterRecord] = field(default_factory=list)

    def add(self, *, reason: str, payload: ExtractionBase) -> None:
        payload_json = payload.model_dump_json(by_alias=True, exclude_none=True)
        digest = hashlib.sha256(payload_json.encode()).hexdigest()
        self.records.append(
            DeadLetterRecord(
                reason=reason, payload_hash=digest, timestamp=datetime.now(timezone.utc)
            )
        )

    def __iter__(self):  # pragma: no cover - convenience
        return iter(self.records)


class ExtractionValidationError(ValueError):
    pass


class ExtractionValidator:
    """Apply semantic validation to extraction payloads."""

    def __init__(self, *, facet_token_budget: int = 120, full_token_budget: int = 2000) -> None:
        self._facet_budget = facet_token_budget
        self._full_budget = full_token_budget
        self.dead_letter = DeadLetterQueue()

    def validate(self, extraction: ExtractionBase, *, text: str, facet_mode: bool = False) -> None:
        try:
            self._validate_spans(extraction, text=text)
            if isinstance(extraction, DoseExtraction):
                self._validate_dose(extraction)
            if isinstance(extraction, EffectExtraction):
                self._validate_effect(extraction)
            if isinstance(extraction, AdverseEventExtraction):
                self._validate_adverse_event(extraction)
            if isinstance(extraction, EligibilityExtraction):
                self._validate_eligibility(extraction)
            self._validate_token_budget(extraction, facet_mode=facet_mode)
        except ExtractionValidationError as exc:
            self.dead_letter.add(reason=str(exc), payload=extraction)
            raise

    def _validate_spans(self, extraction: ExtractionBase, *, text: str) -> None:
        length = len(text)
        for span in extraction.evidence_spans:
            if span.start < 0 or span.end > length or span.start >= span.end:
                raise ExtractionValidationError("evidence span outside chunk bounds")
            expected = text[span.start : span.end]
            if span.quote and span.quote.strip() not in expected.strip():
                raise ExtractionValidationError("evidence span quote mismatch")

    def _validate_dose(self, extraction: DoseExtraction) -> None:
        if extraction.unit and extraction.amount is None:
            raise ExtractionValidationError("dose unit requires amount")
        if extraction.unit and not extraction.unit.replace("/", "").replace(".", "").isalnum():
            raise ExtractionValidationError("invalid UCUM unit")

    def _validate_effect(self, extraction: EffectExtraction) -> None:
        if extraction.measure_type in {"HR", "RR", "OR"} and extraction.value <= 0:
            raise ExtractionValidationError("ratio effect must be > 0")
        if (
            extraction.ci_low is not None
            and extraction.ci_high is not None
            and not (extraction.ci_low <= extraction.value <= extraction.ci_high)
        ):
            raise ExtractionValidationError("effect outside confidence interval")

    def _validate_adverse_event(self, extraction: AdverseEventExtraction) -> None:
        if extraction.grade is not None and extraction.grade not in {1, 2, 3, 4, 5}:
            raise ExtractionValidationError("invalid CTCAE grade")

    def _validate_eligibility(self, extraction: EligibilityExtraction) -> None:
        for criterion in extraction.criteria:
            if criterion.logic and criterion.logic.age:
                gte = criterion.logic.age.get("gte")
                lte = criterion.logic.age.get("lte")
                if gte is not None and lte is not None and gte > lte:
                    raise ExtractionValidationError("age range inconsistent")

    def _validate_token_budget(self, extraction: ExtractionBase, *, facet_mode: bool) -> None:
        budget = self._facet_budget if facet_mode else self._full_budget
        tokens = count_tokens(extraction.model_dump_json(by_alias=True))
        if tokens > budget:
            raise ExtractionValidationError(f"extraction exceeds token budget ({tokens}>{budget})")


__all__ = ["DeadLetterQueue", "ExtractionValidator", "ExtractionValidationError"]
