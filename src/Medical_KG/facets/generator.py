"""Facet generation helpers with strict typing."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import TypeAdapter, ValidationError

from Medical_KG.facets.models import (
    AdverseEventFacet,
    DoseFacet,
    EndpointFacet,
    EvidenceSpan,
    FacetModel,
    FacetType,
    PICOFacet,
)
from Medical_KG.facets.normalizer import drop_low_confidence_codes, normalize_facets
from Medical_KG.facets.tokenizer import count_tokens

INTERVENTION_PATTERN = re.compile(r"\b(treatment|drug|therapy|enalapril|placebo)\b", re.I)
OUTCOME_PATTERN = re.compile(r"\b(mortality|survival|event|nausea)\b", re.I)
POPULATION_PATTERN = re.compile(r"\bpatients?\b", re.I)


@dataclass(slots=True)
class GenerationRequest:
    chunk_id: str
    text: str
    section: str | None = None


def _span_for(text: str, phrase: str) -> EvidenceSpan | None:
    index = text.lower().find(phrase.lower())
    if index == -1:
        return None
    return EvidenceSpan(start=index, end=index + len(phrase), quote=text[index : index + len(phrase)])


def _ensure_spans(spans: Sequence[EvidenceSpan | None], *, fallback_text: str) -> list[EvidenceSpan]:
    filtered = [span for span in spans if span is not None]
    if filtered:
        return filtered
    return [EvidenceSpan(start=0, end=min(len(fallback_text), 120), quote=fallback_text[:120])]


def _generate_pico(text: str) -> PICOFacet | None:
    population_match = POPULATION_PATTERN.search(text)
    if not population_match:
        return None
    interventions = INTERVENTION_PATTERN.findall(text)
    outcomes = OUTCOME_PATTERN.findall(text)
    evidence = _ensure_spans(
        [
            _span_for(text, population_match.group(0)),
            _span_for(text, interventions[0]) if interventions else None,
            _span_for(text, outcomes[0]) if outcomes else None,
        ],
        fallback_text=text,
    )
    return PICOFacet(
        population=population_match.group(0),
        interventions=list(dict.fromkeys(interventions)),
        outcomes=list(dict.fromkeys(outcomes)),
        comparators=["placebo"] if "placebo" in text.lower() else [],
        timeframe=None,
        evidence_spans=evidence,
    )


def _generate_endpoint(text: str) -> EndpointFacet | None:
    match = re.search(r"(hazard ratio|hr)\s*(?P<value>\d+(?:\.\d+)?)", text, re.I)
    if not match:
        return None
    value = float(match.group("value"))
    effect_type: Literal["HR", "RR", "OR", "MD", "SMD"] = "HR"
    name = "hazard ratio"
    evidence = _ensure_spans([_span_for(text, match.group(0))], fallback_text=text)
    return EndpointFacet(
        name=name,
        effect_type=effect_type,
        value=value,
        evidence_spans=evidence,
        outcome_codes=[],
    )


def _generate_ae(text: str) -> AdverseEventFacet | None:
    match = re.search(r"grade\s*(?P<grade>[1-5])\s*(?P<term>[A-Za-z]+)", text, re.I)
    if not match:
        return None
    evidence = _ensure_spans([_span_for(text, match.group(0))], fallback_text=text)
    facet = AdverseEventFacet(
        term=match.group("term"),
        grade=int(match.group("grade")),
        count=None,
        denom=None,
        arm="treatment" if "treatment" in text.lower() else None,
        evidence_spans=evidence,
    )
    return facet


def _generate_dose(text: str) -> DoseFacet | None:
    match = re.search(r"([A-Z][A-Za-z0-9]+)\s+(\d+(?:\.\d+)?)\s*(mg|mcg)\s*(po|iv|bid|tid)?", text)
    if not match:
        return None
    drug = match.group(1)
    amount = float(match.group(2))
    unit = match.group(3).upper()
    schedule = match.group(4)
    evidence = _ensure_spans([_span_for(text, match.group(0))], fallback_text=text)
    return DoseFacet(
        drug_label=drug,
        amount=amount,
        unit=unit,
        route=schedule.upper() if schedule and schedule.lower() in {"po", "iv"} else None,
        frequency_per_day=2.0 if schedule and schedule.lower() == "bid" else None,
        evidence_spans=evidence,
    )


FACET_GENERATORS: dict[FacetType, Callable[[str], FacetModel | None]] = {
    FacetType.PICO: _generate_pico,
    FacetType.ENDPOINT: _generate_endpoint,
    FacetType.ADVERSE_EVENT: _generate_ae,
    FacetType.DOSE: _generate_dose,
}

_facet_adapter: TypeAdapter[FacetModel] = TypeAdapter(FacetModel)


class FacetGenerationError(RuntimeError):
    """Raised when generation fails validation."""


def generate_facet(text: str, facet_type: FacetType) -> FacetModel | None:
    generator = FACET_GENERATORS.get(facet_type)
    if generator is None:
        return None
    facet = generator(text)
    if facet is None:
        return None
    return facet


def validate_budget(facet: FacetModel, *, max_tokens: int = 120) -> FacetModel:
    json_payload = facet.model_dump_json()
    tokens = count_tokens(json_payload)
    if tokens <= max_tokens:
        return facet
    # remove optional fields greedily according to facet type
    if isinstance(facet, EndpointFacet):
        facet.model = None
        facet.arm_sizes = None
        facet.time_unit_ucum = None
        facet.outcome_codes = []
    elif isinstance(facet, AdverseEventFacet):
        facet.codes = []
        facet.arm = None
    elif isinstance(facet, DoseFacet):
        facet.drug_codes = []
        facet.duration_days = None
    elif isinstance(facet, PICOFacet):
        facet.comparators = []
        facet.timeframe = None
    json_payload = facet.model_dump_json()
    tokens = count_tokens(json_payload)
    if tokens > max_tokens:
        raise FacetGenerationError(
            f"Facet exceeds {max_tokens} tokens after compression (actual={tokens})"
        )
    return facet


def generate_facets(
    request: GenerationRequest, facet_types: Iterable[FacetType]
) -> list[FacetModel]:
    facets: list[FacetModel] = []
    for facet_type in facet_types:
        if facet_type in {FacetType.GENERAL, FacetType.ELIGIBILITY}:
            continue
        facet = generate_facet(request.text, facet_type)
        if facet is None:
            continue
        validated = validate_budget(facet)
        facets.append(validated)
    normalized = normalize_facets(facets, text=request.text)
    cleaned = drop_low_confidence_codes(normalized)
    return cleaned


def serialize_facets(facets: Sequence[FacetModel]) -> list[str]:
    serialized: list[str] = []
    for facet in facets:
        serialized.append(facet.model_dump_json(by_alias=True))
    return serialized


def load_facets(payloads: Iterable[str]) -> list[FacetModel]:
    models: list[FacetModel] = []
    for payload in payloads:
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:  # pragma: no cover - defensive
            raise FacetGenerationError("Invalid JSON payload") from exc
        try:
            models.append(_facet_adapter.validate_python(data))
        except ValidationError as exc:
            raise FacetGenerationError(str(exc)) from exc
    return models


__all__ = [
    "FacetGenerationError",
    "GenerationRequest",
    "generate_facets",
    "generate_facet",
    "load_facets",
    "serialize_facets",
    "validate_budget",
]
