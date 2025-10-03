"""Rule-based clinical extraction implementation used for tests."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Iterable

from Medical_KG.facets.models import EvidenceSpan

from .models import (
    AdverseEventExtraction,
    DoseExtraction,
    EffectExtraction,
    EligibilityCriterion,
    EligibilityExtraction,
    EligibilityLogic,
    ExtractionBase,
    ExtractionEnvelope,
    ExtractionType,
    PICOExtraction,
)
from .normalizers import normalise_extractions
from .prompts import PromptLibrary
from .validator import DeadLetterRecord, ExtractionValidationError, ExtractionValidator

P_VALUE_PATTERN = re.compile(r"p\s*(?:=|<)\s*(?P<value>[0-9.]+)", re.I)
CI_PATTERN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:–|-|to)\s*(\d+(?:\.\d+)?)")


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    text: str
    doc_id: str | None = None
    section: str | None = None


def _span(text: str, phrase: str) -> EvidenceSpan | None:
    index = text.lower().find(phrase.lower())
    if index == -1:
        return None
    return EvidenceSpan(
        start=index, end=index + len(phrase), quote=text[index : index + len(phrase)]
    )


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
    extractions: list[ExtractionBase]


ExtractorFn = Callable[[Chunk], list[ExtractionBase] | ExtractionBase | None]


class ClinicalExtractionService:
    """Coordinates extraction across chunk types."""

    def __init__(
        self,
        model_name: str = "qwen2",
        model_version: str = "0.1.0",
        *,
        max_retries: int = 2,
    ) -> None:
        self._model_name = model_name
        self._model_version = model_version
        self._prompts = PromptLibrary()
        self._validator = ExtractionValidator()
        self._max_retries = max_retries
        self._extractors: list[tuple[ExtractionType, ExtractorFn]] = [
            (ExtractionType.PICO, extract_pico),
            (ExtractionType.EFFECT, extract_effects),
            (ExtractionType.ADVERSE_EVENT, extract_ae),
            (ExtractionType.DOSE, extract_dose),
            (ExtractionType.ELIGIBILITY, extract_eligibility),
        ]

    def extract(self, chunk: Chunk) -> list[ExtractionBase]:
        results: list[ExtractionBase] = []
        for extraction_type, extractor in self._extractors:
            if not self._should_extract(extraction_type, chunk):
                continue
            payload = self._invoke_with_retry(extractor, chunk)
            if not payload:
                continue
            items = payload if isinstance(payload, list) else [payload]
            normalised = normalise_extractions(items, text=chunk.text)
            for item in normalised:
                try:
                    self._validator.validate(item, text=chunk.text, facet_mode=False)
                except ExtractionValidationError:
                    continue
                results.append(item)
        return results

    def extract_many(self, chunks: Iterable[Chunk]) -> ExtractionEnvelope:
        chunk_ids: list[str] = []
        payload: list[ExtractionBase] = []
        for chunk in chunks:
            chunk_ids.append(chunk.chunk_id)
            payload.extend(self.extract(chunk))
        schema_hash = hashlib.sha256(
            "::".join(
                sorted(extraction_type.value for extraction_type, _ in self._extractors)
            ).encode()
        ).hexdigest()
        prompt_hash = self._prompts.prompt_hash()
        extracted_at = datetime.now(timezone.utc)
        return ExtractionEnvelope(
            model=self._model_name,
            version=self._model_version,
            prompt_hash=prompt_hash,
            schema_hash=schema_hash,
            ts=datetime.now(timezone.utc),
            extracted_at=extracted_at,
            chunk_ids=chunk_ids,
            payload=payload,
        )

    @property
    def dead_letter(self) -> list[DeadLetterRecord]:  # pragma: no cover - convenience
        return list(self._validator.dead_letter.records)

    def _invoke_with_retry(
        self, extractor: ExtractorFn, chunk: Chunk
    ) -> list[ExtractionBase] | ExtractionBase | None:
        last_error: Exception | None = None
        for _ in range(self._max_retries + 1):
            try:
                return extractor(chunk)
            except Exception as exc:  # noqa: BLE001 - propagate after retries
                last_error = exc
        if last_error:
            raise last_error
        return None

    def _should_extract(self, extraction_type: ExtractionType, chunk: Chunk) -> bool:
        if not chunk.section:
            return True
        section = chunk.section.lower()
        routing = {
            ExtractionType.PICO: {"abstract", "methods", "registry", "results"},
            ExtractionType.EFFECT: {"results", "outcome", "efficacy"},
            ExtractionType.ADVERSE_EVENT: {"adverse", "safety", "ae", "results"},
            ExtractionType.DOSE: {"dosage", "arms", "treatment", "results"},
            ExtractionType.ELIGIBILITY: {"eligibility", "criteria"},
        }
        allowed = routing.get(extraction_type)
        if not allowed:
            return True
        return any(token in section for token in allowed)
