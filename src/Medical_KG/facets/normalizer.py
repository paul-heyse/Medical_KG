"""Post-generation facet normalization utilities."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass

from Medical_KG.facets.models import (
    AdverseEventFacet,
    DoseFacet,
    EndpointFacet,
    FacetModel,
)

CI_PATTERN = re.compile(r"(?P<low>-?\d+(?:\.\d+)?)\s*(?:–|-|to|,)\s*(?P<high>-?\d+(?:\.\d+)?)")
P_VALUE_PATTERN = re.compile(r"p\s*(?:=|<|≤)\s*(?P<value>[0-9.]+)", re.I)
COUNT_PATTERN = re.compile(r"(?P<count>\d+)\s*/\s*(?P<denom>\d+)")
GRADE_PATTERN = re.compile(r"grade\s*(?P<grade>[1-5])", re.I)
DOSE_PATTERN = re.compile(
    r"(?P<drug>[A-Za-z][A-Za-z0-9 -]+)\s+(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>mg|mcg|g|ml)\s*(?P<route>po|iv|im|sc)?\s*(?P<schedule>bid|tid|qid|q\d+h)?",
    re.I,
)
FREQUENCY_MAP = {
    "qd": 1.0,
    "bid": 2.0,
    "tid": 3.0,
    "qid": 4.0,
}


def _parse_ci(text: str) -> tuple[float | None, float | None]:
    match = CI_PATTERN.search(text)
    if not match:
        return None, None
    return float(match.group("low")), float(match.group("high"))


def _parse_p_value(text: str) -> str | None:
    match = P_VALUE_PATTERN.search(text)
    if not match:
        return None
    value = match.group("value")
    operator = "=" if "=" in match.group(0) else "<"
    return f"{operator}{value}"


def _parse_count(text: str) -> tuple[int | None, int | None]:
    match = COUNT_PATTERN.search(text)
    if not match:
        return None, None
    return int(match.group("count")), int(match.group("denom"))


def _parse_grade(text: str) -> int | None:
    match = GRADE_PATTERN.search(text)
    if not match:
        return None
    return int(match.group("grade"))


def normalize_endpoint(facet: EndpointFacet, *, text: str) -> EndpointFacet:
    ci_low, ci_high = _parse_ci(text)
    if ci_low is not None and ci_high is not None:
        facet.ci_low = ci_low
        facet.ci_high = ci_high
    p_value = _parse_p_value(text)
    if p_value is not None:
        facet.p_value = p_value
    return facet


def normalize_adverse_event(facet: AdverseEventFacet, *, text: str) -> AdverseEventFacet:
    grade = _parse_grade(text)
    if grade is not None:
        facet.grade = grade
    count, denom = _parse_count(text)
    if count is not None:
        facet.count = count
    if denom is not None:
        facet.denom = denom
    facet.serious = bool(re.search(r"serious adverse", text, re.I)) or facet.serious
    return facet


def normalize_dose(facet: DoseFacet, *, text: str) -> DoseFacet:
    match = DOSE_PATTERN.search(text)
    if not match:
        return facet
    facet.drug_label = match.group("drug").strip()
    facet.amount = float(match.group("amount"))
    unit = match.group("unit")
    facet.unit = unit.upper() if unit else None
    route = match.group("route")
    if route:
        facet.route = route.upper()
    schedule = match.group("schedule")
    if schedule:
        schedule_lower = schedule.lower()
        facet.frequency_per_day = FREQUENCY_MAP.get(schedule_lower, 1.0)
    return facet


@dataclass(slots=True)
class NormalizationPlan:
    """Defines which normalizers to apply for a generated facet."""

    facet: FacetModel
    text: str

    def execute(self) -> FacetModel:
        if isinstance(self.facet, EndpointFacet):
            return normalize_endpoint(self.facet, text=self.text)
        if isinstance(self.facet, AdverseEventFacet):
            return normalize_adverse_event(self.facet, text=self.text)
        if isinstance(self.facet, DoseFacet):
            return normalize_dose(self.facet, text=self.text)
        return self.facet


def normalize_facets(facets: Iterable[FacetModel], *, text: str) -> list[FacetModel]:
    return [NormalizationPlan(facet=facet, text=text).execute() for facet in facets]


def drop_low_confidence_codes(facets: Iterable[FacetModel]) -> list[FacetModel]:
    sanitized: list[FacetModel] = []
    for facet in facets:
        if isinstance(facet, EndpointFacet):
            facet.outcome_codes = [
                code for code in facet.outcome_codes if (code.confidence or 0) >= 0.5
            ]
        elif isinstance(facet, AdverseEventFacet):
            facet.codes = [code for code in facet.codes if (code.confidence or 0) >= 0.5]
        elif isinstance(facet, DoseFacet):
            facet.drug_codes = [code for code in facet.drug_codes if (code.confidence or 0) >= 0.5]
        sanitized.append(facet)
    return sanitized
