"""Validation helpers for facet payloads."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Sequence

from .models import AdverseEventFacet, DoseFacet, EndpointFacet, FacetModel
from .tokenizer import count_tokens


class FacetValidationError(ValueError):
    """Raised when a facet fails validation."""


@dataclass(slots=True)
class FacetValidator:
    """Apply structural and semantic validation to facets."""

    allowed_ucum_units: set[str] = field(
        default_factory=lambda: {
            "MG",
            "MCG",
            "G",
            "KG",
            "ML",
            "L",
            "MG/ML",
            "MG/DAY",
            "MG/KG",
            "MMOL/L",
        }
    )

    def validate(self, facet: FacetModel, *, text: str) -> FacetModel:
        self._validate_spans(facet, text=text)
        if isinstance(facet, DoseFacet):
            self._validate_dose(facet)
        if isinstance(facet, EndpointFacet):
            self._validate_endpoint(facet)
        if isinstance(facet, AdverseEventFacet):
            self._validate_adverse_event(facet)
        self._validate_token_budget(facet)
        return facet

    def _validate_spans(self, facet: FacetModel, *, text: str) -> None:
        length = len(text)
        for span in facet.evidence_spans:
            if span.start < 0 or span.end > length or span.start >= span.end:
                msg = f"Span offsets out of range for facet type={facet.type}"
                raise FacetValidationError(msg)
            snippet = text[span.start : span.end]
            if span.quote and span.quote.strip() not in snippet.strip():
                msg = "Span quote does not match source text"
                raise FacetValidationError(msg)

    def _validate_dose(self, facet: DoseFacet) -> None:
        if facet.unit and facet.amount is None:
            facet.unit = None
        if facet.unit and facet.unit.upper() not in self.allowed_ucum_units:
            msg = f"Unsupported UCUM unit '{facet.unit}'"
            raise FacetValidationError(msg)

    def _validate_endpoint(self, facet: EndpointFacet) -> None:
        if facet.effect_type in {"HR", "RR", "OR"} and facet.value <= 0:
            msg = "Ratio effects must be > 0"
            raise FacetValidationError(msg)
        if (
            facet.ci_low is not None
            and facet.ci_high is not None
            and not (facet.ci_low <= facet.value <= facet.ci_high)
        ):
            msg = "Effect value must lie within confidence interval"
            raise FacetValidationError(msg)

    def _validate_adverse_event(self, facet: AdverseEventFacet) -> None:
        if facet.grade is not None and facet.grade not in {1, 2, 3, 4, 5}:
            msg = "Adverse event grade must be between 1 and 5"
            raise FacetValidationError(msg)

    def _validate_token_budget(self, facet: FacetModel) -> None:
        tokens = count_tokens(facet.model_dump_json(by_alias=True))
        if tokens > facet.token_budget:
            msg = f"Facet exceeds token budget ({tokens}>{facet.token_budget})"
            raise FacetValidationError(msg)


def validate_facets(facets: Sequence[FacetModel], *, text: str) -> list[FacetModel]:
    validator = FacetValidator()
    return [validator.validate(facet, text=text) for facet in facets]


__all__ = ["FacetValidator", "FacetValidationError", "validate_facets"]
