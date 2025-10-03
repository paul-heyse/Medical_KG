"""Prompt templates for clinical extraction LLM calls."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Dict

from .models import ExtractionType


GLOBAL_RULES = [
    "Return valid JSON only (no prose).",
    "Extract facts verbatim from the provided chunk; never infer or paraphrase.",
    "Provide evidence_spans for every extracted field.",
    "Omit any field that is not explicitly present in the text.",
]


@dataclass(slots=True)
class PromptTemplate:
    name: str
    system: str
    user: str


@dataclass(slots=True)
class Prompt:
    system: str
    user: str
    name: str


class PromptLibrary:
    """Central registry of extraction prompts."""

    def __init__(self) -> None:
        self._templates: Dict[ExtractionType, PromptTemplate] = {
            ExtractionType.PICO: PromptTemplate(
                name="pico",
                system=(
                    "You are extracting Population, Interventions (with dosing), Comparators, Outcomes,"
                    " and Timeframe. Use the exact words from the text and produce compact arrays."
                ),
                user="Extract PICO facts from the following chunk:\n{text}",
            ),
            ExtractionType.EFFECT: PromptTemplate(
                name="effects",
                system=(
                    "Identify effect measures (HR, RR, OR, MD, SMD) with value, confidence interval,"
                    " p_value, n_total, arm_sizes, model, time_unit_ucum when stated."
                ),
                user="Extract effect measures from the following chunk:\n{text}",
            ),
            ExtractionType.ADVERSE_EVENT: PromptTemplate(
                name="ae",
                system=(
                    "Extract adverse events with MedDRA Preferred Terms, grade, count/denom, arm,"
                    " serious flag, and onset_days when reported."
                ),
                user="Extract adverse events from the following chunk:\n{text}",
            ),
            ExtractionType.DOSE: PromptTemplate(
                name="dose",
                system=(
                    "Extract dosing regimens including drug label, amount, UCUM unit, route,"
                    " frequency_per_day, and duration_days."
                ),
                user="Extract dosing instructions from the following chunk:\n{text}",
            ),
            ExtractionType.ELIGIBILITY: PromptTemplate(
                name="eligibility",
                system=(
                    "Split inclusion vs exclusion criteria, capturing logic for age ranges, lab thresholds"
                    " (with LOINC + UCUM), conditions (with codes), and temporal constraints."
                ),
                user="Extract eligibility criteria from the following chunk:\n{text}",
            ),
        }

    def build(self, extraction_type: ExtractionType, *, text: str) -> Prompt:
        template = self._templates[extraction_type]
        system = "\n".join(GLOBAL_RULES + [template.system])
        user = template.user.format(text=text)
        return Prompt(system=system, user=user, name=template.name)

    def prompt_hash(self) -> str:
        serialised = {
            key.value: {"system": tpl.system, "user": tpl.user}
            for key, tpl in sorted(self._templates.items(), key=lambda item: item[0].value)
        }
        blob = json.dumps({"rules": GLOBAL_RULES, "templates": serialised}, sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()


__all__ = ["Prompt", "PromptLibrary", "PromptTemplate", "GLOBAL_RULES"]
