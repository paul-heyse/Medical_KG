from __future__ import annotations

import pytest

from Medical_KG.extraction.models import (
    DoseExtraction,
    EffectExtraction,
    EligibilityCriterion,
    EligibilityExtraction,
    EligibilityLogic,
    ExtractionType,
    PICOExtraction,
)
from Medical_KG.extraction.validator import ExtractionValidationError, ExtractionValidator
from Medical_KG.facets.models import EvidenceSpan


def _span() -> EvidenceSpan:
    return EvidenceSpan(start=0, end=5, quote="token")


def test_validator_detects_span_outside_bounds() -> None:
    extraction = PICOExtraction(
        type=ExtractionType.PICO,
        population="patients",
        interventions=[],
        comparators=[],
        outcomes=[],
        evidence_spans=[EvidenceSpan(start=0, end=50, quote="patients")],
    )
    validator = ExtractionValidator()
    with pytest.raises(ExtractionValidationError):
        validator.validate(extraction, text="pat", facet_mode=False)


def test_validator_detects_quote_mismatch() -> None:
    extraction = PICOExtraction(
        type=ExtractionType.PICO,
        population="patients",
        interventions=[],
        comparators=[],
        outcomes=[],
        evidence_spans=[EvidenceSpan(start=0, end=5, quote="other")],
    )
    validator = ExtractionValidator()
    with pytest.raises(ExtractionValidationError):
        validator.validate(extraction, text="match", facet_mode=False)


def test_validator_requires_amount_when_unit_present() -> None:
    extraction = DoseExtraction(
        type=ExtractionType.DOSE,
        unit="mg",
        amount=None,
        evidence_spans=[_span()],
    )
    validator = ExtractionValidator()
    with pytest.raises(ExtractionValidationError):
        validator.validate(extraction, text="dose", facet_mode=False)


def test_validator_bounds_effect_value() -> None:
    extraction = EffectExtraction(
        type=ExtractionType.EFFECT,
        name="hr",
        measure_type="HR",
        value=2.0,
        ci_low=2.5,
        ci_high=3.0,
        evidence_spans=[_span()],
    )
    validator = ExtractionValidator()
    with pytest.raises(ExtractionValidationError):
        validator.validate(extraction, text="", facet_mode=False)


def test_validator_catches_invalid_age_range() -> None:
    extraction = EligibilityExtraction(
        type=ExtractionType.ELIGIBILITY,
        category="inclusion",
        criteria=[
            EligibilityCriterion(
                text="Age",
                logic=EligibilityLogic(age={"gte": 70, "lte": 65}),
            )
        ],
        evidence_spans=[_span()],
    )
    validator = ExtractionValidator()
    with pytest.raises(ExtractionValidationError):
        validator.validate(extraction, text="", facet_mode=False)


def test_validator_enforces_token_budget() -> None:
    payload = "word " * 20
    extraction = PICOExtraction(
        type=ExtractionType.PICO,
        population=payload,
        interventions=[],
        comparators=[],
        outcomes=[],
        evidence_spans=[_span()],
    )
    validator = ExtractionValidator(facet_token_budget=5, full_token_budget=10)
    with pytest.raises(ExtractionValidationError):
        validator.validate(extraction, text=payload, facet_mode=True)

