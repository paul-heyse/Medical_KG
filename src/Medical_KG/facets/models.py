"""Typed Pydantic models representing retrieval facets."""

from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator


class EvidenceSpan(BaseModel):
    """Span grounding for facet values."""

    start: int = Field(ge=0)
    end: int = Field(gt=0)
    quote: str = Field(min_length=1)
    doc_id: str | None = Field(default=None, description="Document identifier")

    @model_validator(mode="after")
    def validate_order(self) -> "EvidenceSpan":
        if self.end <= self.start:
            msg = "end must be greater than start"
            raise ValueError(msg)
        return self


class FacetType(str, Enum):
    """Enumeration of supported facet families."""

    PICO = "pico"
    ENDPOINT = "endpoint"
    ADVERSE_EVENT = "ae"
    DOSE = "dose"
    ELIGIBILITY = "eligibility"
    GENERAL = "general"


class Code(BaseModel):
    """Coding for terminology references (RxCUI, LOINC, MedDRA, etc.)."""

    system: str
    code: str
    display: str | None = None
    confidence: float | None = Field(default=None, serialization_alias="__confidence")


class Facet(BaseModel):
    """Base facet definition used for polymorphic responses."""

    type: FacetType
    evidence_spans: Annotated[list[EvidenceSpan], Field(min_length=1)]
    token_budget: int = 120
    is_primary: bool | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)


class PICOFacet(Facet):
    """Population, intervention, comparator, outcome summary."""

    type: Literal[FacetType.PICO] = FacetType.PICO
    population: str | None = None
    interventions: list[str] = Field(default_factory=list)
    comparators: list[str] = Field(default_factory=list)
    outcomes: list[str] = Field(default_factory=list)
    timeframe: str | None = None


class EndpointFacet(Facet):
    """Endpoint effect summary facet."""

    type: Literal[FacetType.ENDPOINT] = FacetType.ENDPOINT
    name: str
    effect_type: Literal["HR", "RR", "OR", "MD", "SMD"]
    value: float
    ci_low: float | None = None
    ci_high: float | None = None
    p_value: str | None = None
    n_total: int | None = Field(default=None, ge=0)
    arm_sizes: list[int] | None = None
    model: str | None = None
    time_unit_ucum: str | None = None
    outcome_codes: list[Code] = Field(default_factory=list)


class AdverseEventFacet(Facet):
    """Adverse event summary facet."""

    type: Literal[FacetType.ADVERSE_EVENT] = FacetType.ADVERSE_EVENT
    term: str
    meddra_pt: str | None = None
    grade: int | None = Field(default=None, ge=1, le=5)
    arm: str | None = None
    count: int | None = Field(default=None, ge=0)
    denom: int | None = Field(default=None, ge=0)
    serious: bool | None = None
    onset_days: float | None = Field(default=None, ge=0)
    codes: list[Code] = Field(default_factory=list)


class DoseFacet(Facet):
    """Dose description facet."""

    type: Literal[FacetType.DOSE] = FacetType.DOSE
    drug_label: str
    drug_codes: list[Code] = Field(default_factory=list)
    amount: float | None = Field(default=None, ge=0)
    unit: str | None = None
    route: str | None = None
    frequency_per_day: float | None = Field(default=None, ge=0)
    duration_days: float | None = Field(default=None, ge=0)
    loinc_section: str | None = None


FacetModel = Annotated[
    PICOFacet | EndpointFacet | AdverseEventFacet | DoseFacet,
    Field(discriminator="type"),
]


class FacetIndexRecord(BaseModel):
    """Representation persisted to search index."""

    chunk_id: str
    facets: Sequence[FacetModel]

    @property
    def facet_types(self) -> list[str]:
        return [facet.type.value for facet in self.facets]

    def facet_codes(self) -> list[str]:
        codes: list[str] = []
        for facet in self.facets:
            if isinstance(facet, EndpointFacet):
                codes.extend(code.code for code in facet.outcome_codes)
            elif isinstance(facet, AdverseEventFacet):
                codes.extend(code.code for code in facet.codes)
            elif isinstance(facet, DoseFacet):
                codes.extend(code.code for code in facet.drug_codes)
        return codes


__all__ = [
    "AdverseEventFacet",
    "Code",
    "DoseFacet",
    "EndpointFacet",
    "EvidenceSpan",
    "Facet",
    "FacetIndexRecord",
    "FacetModel",
    "FacetType",
    "PICOFacet",
]
