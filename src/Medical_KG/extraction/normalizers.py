"""Normalisation pipeline for clinical extraction outputs."""

from __future__ import annotations

from typing import Iterable

from .models import (
    AdverseEventExtraction,
    DoseExtraction,
    EffectExtraction,
    EligibilityCriterion,
    EligibilityExtraction,
    EligibilityLogic,
    ExtractionBase,
    PICOExtraction,
)
from .parsers import (
    parse_age_logic,
    parse_confidence_interval,
    parse_count,
    parse_lab_threshold,
    parse_p_value,
    parse_temporal_constraint,
)
from .resolvers import resolve_drug, resolve_lab, resolve_meddra


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        key = value.strip()
        if not key or key.lower() in seen:
            continue
        seen.add(key.lower())
        ordered.append(key)
    return ordered


def normalise_pico(extraction: PICOExtraction) -> PICOExtraction:
    extraction.interventions = _dedupe(extraction.interventions)
    extraction.comparators = _dedupe(extraction.comparators)
    extraction.outcomes = _dedupe(extraction.outcomes)
    return extraction


def normalise_effect(extraction: EffectExtraction, *, text: str) -> EffectExtraction:
    ci_low, ci_high = parse_confidence_interval(text)
    if ci_low is not None:
        extraction.ci_low = ci_low
    if ci_high is not None:
        extraction.ci_high = ci_high
    if (p_value := parse_p_value(text)) is not None:
        extraction.p_value = p_value
    count, denom = parse_count(text)
    if count is not None and extraction.arm_sizes is None:
        extraction.arm_sizes = [count]
    if denom is not None and extraction.n_total is None:
        extraction.n_total = denom
    return extraction


def normalise_adverse_event(
    extraction: AdverseEventExtraction, *, text: str
) -> AdverseEventExtraction:
    if extraction.codes:
        extraction.codes = [code for code in extraction.codes if (code.confidence or 0) >= 0.5]
    if not extraction.codes:
        extraction.codes = resolve_meddra(extraction.term)
    count, denom = parse_count(text)
    if count is not None:
        extraction.count = count
    if denom is not None:
        extraction.denom = denom
    if "serious" in text.lower():
        extraction.serious = True
    return extraction


_ROUTE_MAP = {
    "oral": "PO",
    "po": "PO",
    "intravenous": "IV",
    "iv": "IV",
}

_FREQUENCY_MAP = {
    "bid": 2.0,
    "tid": 3.0,
    "qid": 4.0,
    "q12h": 2.0,
}


def normalise_dose(extraction: DoseExtraction, *, text: str) -> DoseExtraction:
    if extraction.drug:
        codes = resolve_drug(extraction.drug.display or extraction.drug.code)
        extraction.drug = extraction.drug
        extraction.drug_codes = codes
    elif extraction.drug is None and extraction.amount is not None:
        extraction.drug_codes = resolve_drug(text.split()[0])
    if extraction.unit:
        extraction.unit = extraction.unit.upper()
    if extraction.route:
        extraction.route = _ROUTE_MAP.get(extraction.route.lower(), extraction.route.upper())
    if extraction.frequency_per_day is None:
        for key, value in _FREQUENCY_MAP.items():
            if key in text.lower():
                extraction.frequency_per_day = value
                break
    return extraction


def normalise_eligibility(extraction: EligibilityExtraction, *, text: str) -> EligibilityExtraction:
    updated: list[EligibilityCriterion] = []
    for criterion in extraction.criteria:
        logic = criterion.logic or EligibilityLogic()
        if logic.age is None:
            age_logic = parse_age_logic(criterion.text)
            if age_logic:
                logic.age = age_logic
        if logic.lab is None:
            lab = parse_lab_threshold(criterion.text)
            if lab:
                codes = resolve_lab(lab["label"])
                if codes:
                    logic.lab = {
                        "loinc": codes[0].code,
                        "op": lab["op"],
                        "value": lab["value"],
                        "unit": lab["unit"],
                    }
        if logic.temporal is None:
            temporal = parse_temporal_constraint(criterion.text)
            if temporal:
                logic.temporal = temporal
        updated.append(EligibilityCriterion(text=criterion.text, logic=logic))
    extraction.criteria = updated
    return extraction


def normalise_extraction(extraction: ExtractionBase, *, text: str) -> ExtractionBase:
    if isinstance(extraction, PICOExtraction):
        return normalise_pico(extraction)
    if isinstance(extraction, EffectExtraction):
        return normalise_effect(extraction, text=text)
    if isinstance(extraction, AdverseEventExtraction):
        return normalise_adverse_event(extraction, text=text)
    if isinstance(extraction, DoseExtraction):
        return normalise_dose(extraction, text=text)
    if isinstance(extraction, EligibilityExtraction):
        return normalise_eligibility(extraction, text=text)
    return extraction


def normalise_extractions(
    extractions: Iterable[ExtractionBase], *, text: str
) -> list[ExtractionBase]:
    return [normalise_extraction(extraction, text=text) for extraction in extractions]


__all__ = ["normalise_extractions", "normalise_extraction"]
