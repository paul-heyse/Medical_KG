"""Pydantic models and validation for clinical extractions."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Literal

from Medical_KG.facets.models import Code, EvidenceSpan
from pydantic import BaseModel, Field, model_validator


class ExtractionType(str, Enum):
    PICO = "pico"
    EFFECT = "effects"
    ADVERSE_EVENT = "ae"
    DOSE = "dose"
    ELIGIBILITY = "eligibility"


class ExtractionBase(BaseModel):
    type: ExtractionType
    evidence_spans: Annotated[list[EvidenceSpan], Field(min_length=1)]
    confidence: Annotated[float | None, Field(default=None, serialization_alias="__confidence")]


class PICOExtraction(ExtractionBase):
    type: Literal[ExtractionType.PICO] = ExtractionType.PICO
    population: str
    interventions: Annotated[list[str], Field(default_factory=list)]
    comparators: Annotated[list[str], Field(default_factory=list)]
    outcomes: Annotated[list[str], Field(default_factory=list)]
    timeframe: str | None = None


class EffectExtraction(ExtractionBase):
    type: Literal[ExtractionType.EFFECT] = ExtractionType.EFFECT
    name: str
    measure_type: Literal["HR", "RR", "OR", "MD", "SMD"]
    value: float
    ci_low: float | None = None
    ci_high: float | None = None
    p_value: str | None = None
    n_total: Annotated[int | None, Field(default=None, ge=0)]
    arm_sizes: list[int] | None = None
    model: str | None = None
    time_unit_ucum: str | None = None


class AdverseEventExtraction(ExtractionBase):
    type: Literal[ExtractionType.ADVERSE_EVENT] = ExtractionType.ADVERSE_EVENT
    term: str
    meddra_pt: str | None = None
    grade: Annotated[int | None, Field(default=None, ge=1, le=5)]
    count: Annotated[int | None, Field(default=None, ge=0)]
    denom: Annotated[int | None, Field(default=None, ge=0)]
    arm: str | None = None
    serious: bool | None = None
    onset_days: Annotated[float | None, Field(default=None, ge=0)]
    codes: Annotated[list[Code], Field(default_factory=list)]


class DoseExtraction(ExtractionBase):
    type: Literal[ExtractionType.DOSE] = ExtractionType.DOSE
    drug: Code | None = None
    amount: Annotated[float | None, Field(default=None, ge=0)]
    unit: str | None = None
    route: str | None = None
    frequency_per_day: Annotated[float | None, Field(default=None, ge=0)]
    duration_days: Annotated[float | None, Field(default=None, ge=0)]
    drug_codes: Annotated[list[Code], Field(default_factory=list)]


class EligibilityLogic(BaseModel):
    age: dict[str, float] | None = None
    lab: dict[str, str | float] | None = None
    condition: dict[str, str] | None = None
    temporal: dict[str, str | float] | None = None


class EligibilityCriterion(BaseModel):
    text: str
    logic: EligibilityLogic | None = None


class EligibilityExtraction(ExtractionBase):
    type: Literal[ExtractionType.ELIGIBILITY] = ExtractionType.ELIGIBILITY
    category: Literal["inclusion", "exclusion"]
    criteria: list[EligibilityCriterion]

    @model_validator(mode="after")
    def ensure_criteria(self) -> "EligibilityExtraction":
        if not self.criteria:
            msg = "Eligibility extraction must include criteria"
            raise ValueError(msg)
        return self


class ExtractionEnvelope(BaseModel):
    """Wraps extraction payloads with provenance metadata."""

    model: str
    version: str
    prompt_hash: str
    schema_hash: str
    ts: datetime
    extracted_at: datetime
    chunk_ids: list[str]
    payload: list[ExtractionBase]
