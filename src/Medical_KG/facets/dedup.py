"""Utilities for deduplicating facet payloads at document scope."""

from __future__ import annotations

import re
from collections import OrderedDict
from typing import Iterable

from .models import AdverseEventFacet, EndpointFacet, FacetModel


def _normalise(text: str | None) -> str:
    if not text:
        return ""
    collapsed = re.sub(r"\s+", " ", text).strip().lower()
    return collapsed


def _endpoint_key(facet: EndpointFacet) -> tuple[str, ...] | None:
    codes = tuple(sorted(code.code.lower() for code in facet.outcome_codes if code.code))
    name = _normalise(facet.name)
    if not codes and not name:
        return None
    anchor = codes or (name,)
    return (
        "endpoint",
        *anchor,
        facet.effect_type.upper(),
        _normalise(facet.time_unit_ucum),
    )


def _ae_key(facet: AdverseEventFacet) -> tuple[str, ...] | None:
    term = _normalise(facet.meddra_pt or facet.term)
    if not term:
        return None
    return (
        "ae",
        term,
        str(facet.grade or 0),
        _normalise(facet.arm),
    )


def _score(facet: FacetModel) -> float:
    if facet.confidence is not None:
        return facet.confidence
    return float(len(facet.evidence_spans))


def deduplicate_facets(facets: Iterable[FacetModel]) -> list[FacetModel]:
    """Collapse duplicate endpoint/AE facets while marking primaries."""

    primaries: OrderedDict[tuple[str, ...], FacetModel] = OrderedDict()
    passthrough: list[FacetModel] = []
    for facet in facets:
        key: tuple[str, ...] | None = None
        if isinstance(facet, EndpointFacet):
            key = _endpoint_key(facet)
        elif isinstance(facet, AdverseEventFacet):
            key = _ae_key(facet)
        if key is None:
            passthrough.append(facet)
            continue
        best = primaries.get(key)
        if best is None or _score(facet) > _score(best):
            primaries[key] = facet
    deduped = passthrough + list(primaries.values())
    for facet in primaries.values():
        facet.is_primary = True
    return deduped


__all__ = ["deduplicate_facets"]
