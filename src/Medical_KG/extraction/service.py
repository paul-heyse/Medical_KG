"""Rule-based clinical extraction implementation used for tests."""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from Medical_KG.facets.models import EvidenceSpan
from Medical_KG.extraction.models import (
    AdverseEventExtraction,
    DoseExtraction,
    EffectExtraction,
    EligibilityCriterion,
    EligibilityExtraction,
    EligibilityLogic,
    ExtractionEnvelope,
    ExtractionType,
    PICOExtraction,
)

P_VALUE_PATTERN = re.compile(r"p\s*(?:=|<)\s*(?P<value>[0-9.]+)", re.I)
CI_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:–|-|to)\s*(\d+(?:\.\d+)?)")


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    text: str


def _span(text: str, phrase: str) -> EvidenceSpan | None:
    index = text.lower().find(phrase.lower())
    if index == -1:
        return None
    return EvidenceSpan(start=index, end=index + len(phrase), quote=text[index : index + len(phrase)])


def _ensure_span(span: EvidenceSpan | None, text: str) -> list[EvidenceSpan]:
    if span is not None:
        return [span]
    return [EvidenceSpan(start=0, end=min(len(text), 80), quote=text[:80])]


def extract_pico(chunk: Chunk) -> PICOExtraction | None:
    if "patients" not in chunk.text.lower():
        return None
    interventions = []
    if "treatment" in chunk.text.lower():
        interventions.append("treatment")
    if "placebo" in chunk.text.lower():
        interventions.append("placebo")
    outcomes = []
    for term in ["mortality", "survival", "nausea"]:
        if term in chunk.text.lower():
            outcomes.append(term)
    span = _span(chunk.text, "patients")
    return PICOExtraction(
        population="patients",
        interventions=interventions,
        comparators=[item for item in interventions if item == "placebo"],
        outcomes=outcomes,
        timeframe=None,
        evidence_spans=_ensure_span(span, chunk.text),
    )


def extract_effects(chunk: Chunk) -> EffectExtraction | None:
    match = re.search(r"hazard ratio\s*(\d+(?:\.\d+)?)", chunk.text, re.I)
    if not match:
        return None
    value = float(match.group(1))
    ci = CI_PATTERN.search(chunk.text)
    ci_low = float(ci.group(1)) if ci else None
    ci_high = float(ci.group(2)) if ci else None
    p_match = P_VALUE_PATTERN.search(chunk.text)
    p_value = None
    if p_match:
        operator = "=" if "=" in p_match.group(0) else "<"
        p_value = f"{operator}{p_match.group('value')}"
    return EffectExtraction(
        name="hazard ratio",
        measure_type="HR",
        value=value,
        ci_low=ci_low,
        ci_high=ci_high,
        p_value=p_value,
        evidence_spans=_ensure_span(_span(chunk.text, match.group(0)), chunk.text),
    )


def extract_ae(chunk: Chunk) -> AdverseEventExtraction | None:
    match = re.search(r"grade\s*(\d)\s*(\w+)", chunk.text, re.I)
    if not match:
        return None
    grade = int(match.group(1))
    term = match.group(2)
    evidence = _ensure_span(_span(chunk.text, match.group(0)), chunk.text)
    count_match = re.search(r"(\d+)\s*/\s*(\d+)", chunk.text)
    count = int(count_match.group(1)) if count_match else None
    denom = int(count_match.group(2)) if count_match else None
    serious = "serious" in chunk.text.lower()
    return AdverseEventExtraction(
        term=term,
        grade=grade,
        count=count,
        denom=denom,
        serious=serious,
        evidence_spans=evidence,
    )


def extract_dose(chunk: Chunk) -> DoseExtraction | None:
    match = re.search(r"([A-Za-z]+)\s+(\d+(?:\.\d+)?)\s*(mg|mcg)\s*(po|iv|bid)?", chunk.text)
    if not match:
        return None
    amount = float(match.group(2))
    unit = match.group(3).upper()
    route = match.group(4)
    frequency = None
    if route and route.lower() == "bid":
        frequency = 2.0
    return DoseExtraction(
        amount=amount,
        unit=unit,
        route=route.upper() if route and route.lower() in {"po", "iv"} else None,
        frequency_per_day=frequency,
        evidence_spans=_ensure_span(_span(chunk.text, match.group(0)), chunk.text),
    )


def extract_eligibility(chunk: Chunk) -> list[EligibilityExtraction]:
    extractions: list[EligibilityExtraction] = []
    lowered = chunk.text.lower()
    if "inclusion" in lowered:
        logic = EligibilityLogic()
        if match := re.search(r"age\s*(\d+)-(\d+)", lowered):
            logic.age = {"gte": float(match.group(1)), "lte": float(match.group(2))}
        extractions.append(
            EligibilityExtraction(
                category="inclusion",
                criteria=[EligibilityCriterion(text=chunk.text.strip(), logic=logic)],
                evidence_spans=_ensure_span(_span(chunk.text, "inclusion"), chunk.text),
            )
        )
    if "exclusion" in lowered:
        extractions.append(
            EligibilityExtraction(
                category="exclusion",
                criteria=[EligibilityCriterion(text=chunk.text.strip(), logic=None)],
                evidence_spans=_ensure_span(_span(chunk.text, "exclusion"), chunk.text),
            )
        )
    return extractions


@dataclass(slots=True)
class ExtractionResult:
    chunk_id: str
    extractions: list


class ClinicalExtractionService:
    """Coordinates extraction across chunk types."""

    def __init__(self, model_name: str = "qwen2", model_version: str = "0.1.0") -> None:
        self._model_name = model_name
        self._model_version = model_version

    def extract(self, chunk: Chunk) -> list:
        results: list = []
        for extractor in (
            extract_pico,
            extract_effects,
            extract_ae,
            extract_dose,
        ):
            extraction = extractor(chunk)
            if extraction is not None:
                results.append(extraction)
        results.extend(extract_eligibility(chunk))
        return results

    def extract_many(self, chunks: Iterable[Chunk]) -> ExtractionEnvelope:
        chunk_ids: list[str] = []
        payload: list = []
        for chunk in chunks:
            chunk_ids.append(chunk.chunk_id)
            payload.extend(self.extract(chunk))
        schema_hash = hashlib.sha256("clinical-extractions-v1".encode()).hexdigest()
        prompt_hash = hashlib.sha256("clinical-prompts-v1".encode()).hexdigest()
        return ExtractionEnvelope(
            model=self._model_name,
            version=self._model_version,
            prompt_hash=prompt_hash,
            schema_hash=schema_hash,
            ts=datetime.now(timezone.utc),
            chunk_ids=chunk_ids,
            payload=payload,
        )
