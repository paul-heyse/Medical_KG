"""Facet summary generation for semantic chunks."""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Dict, Optional

from .chunker import Chunk
from .tagger import ClinicalIntent

_EFFECT_PATTERN = re.compile(
    r"(?P<metric>HR|OR|RR|hazard ratio|risk ratio|mean difference)(?:\s*(?:was|=|:))?\s*(?P<value>\d+(?:\.\d+)?)",
    re.IGNORECASE,
)
_DOSE_PATTERN = re.compile(r"(?P<amount>\d+(?:\.\d+)?)\s*(?P<unit>mg|ml|g|mcg)")
_LAB_PATTERN = re.compile(r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>mmol/L|g/dL|IU/L)")


@dataclass(slots=True)
class FacetGenerator:
    """Generate compact JSON facets from chunk text."""

    max_tokens: int = 120

    def generate(self, chunk: Chunk) -> None:
        facet: Optional[Dict[str, object]] = None
        facet_type: Optional[str] = None
        text = chunk.text
        if chunk.intent in {ClinicalIntent.ENDPOINT, ClinicalIntent.PICO_OUTCOME}:
            match = _EFFECT_PATTERN.search(text)
            if match:
                facet = {
                    "metric": match.group("metric"),
                    "value": match.group("value"),
                }
                facet_type = "endpoint"
        elif chunk.intent == ClinicalIntent.DOSE:
            match = _DOSE_PATTERN.search(text)
            if match:
                facet = {
                    "amount": match.group("amount"),
                    "unit": match.group("unit"),
                }
                facet_type = "dose"
        elif chunk.intent == ClinicalIntent.LAB_VALUE:
            match = _LAB_PATTERN.search(text)
            if match:
                facet = {
                    "value": match.group("value"),
                    "unit": match.group("unit"),
                }
                facet_type = "lab_value"
        if facet:
            payload = json.dumps(facet)
            if len(payload.split()) > self.max_tokens:
                return
            chunk.facet_json = {key: value for key, value in facet.items()}
            chunk.facet_type = facet_type


__all__ = ["FacetGenerator"]
