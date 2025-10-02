"""Lightweight clinical intent tagging based on heuristics."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Sequence


class ClinicalIntent(str, Enum):
    PICO_POPULATION = "pico_population"
    PICO_INTERVENTION = "pico_intervention"
    PICO_OUTCOME = "pico_outcome"
    ADVERSE_EVENT = "adverse_event"
    DOSE = "dose"
    ELIGIBILITY = "eligibility"
    RECOMMENDATION = "recommendation"
    LAB_VALUE = "lab_value"
    ENDPOINT = "endpoint"
    GENERAL = "general"


@dataclass(slots=True)
class ClinicalIntentTagger:
    """Simple heuristic tagger using keyword cues and section hints."""

    def tag_sentence(self, sentence: str, *, section: str | None = None) -> ClinicalIntent:
        lowered = sentence.lower()
        if section:
            section_lower = section.lower()
            if "adverse" in section_lower:
                return ClinicalIntent.ADVERSE_EVENT
            if "eligibility" in section_lower or "inclusion" in section_lower:
                return ClinicalIntent.ELIGIBILITY
            if "outcome" in section_lower:
                return ClinicalIntent.PICO_OUTCOME
            if "dosage" in section_lower or "dose" in section_lower:
                return ClinicalIntent.DOSE
        if re.search(r"dose|mg|ml", lowered):
            return ClinicalIntent.DOSE
        if re.search(r"patients? aged|men and women|subjects with", lowered):
            return ClinicalIntent.PICO_POPULATION
        if re.search(r"randomized to|administered|received", lowered):
            return ClinicalIntent.PICO_INTERVENTION
        if re.search(r"hazard ratio|odds ratio|p=|confidence interval", lowered):
            return ClinicalIntent.ENDPOINT
        if re.search(r"adverse event|serious adverse", lowered):
            return ClinicalIntent.ADVERSE_EVENT
        if re.search(r"eligibility|exclusion|inclusion", lowered):
            return ClinicalIntent.ELIGIBILITY
        if re.search(r"recommend", lowered):
            return ClinicalIntent.RECOMMENDATION
        if re.search(r"laboratory|lab value|mmol|g/dl", lowered):
            return ClinicalIntent.LAB_VALUE
        return ClinicalIntent.GENERAL

    def tag_sentences(self, sentences: Sequence[str], *, sections: Sequence[str] | None = None) -> List[ClinicalIntent]:
        intents = []
        sections = sections or [None] * len(sentences)
        for sentence, section in zip(sentences, sections):
            intents.append(self.tag_sentence(sentence, section=section))
        return intents

    def dominant_intent(self, intents: Iterable[ClinicalIntent]) -> ClinicalIntent:
        counter = Counter(intents)
        if not counter:
            return ClinicalIntent.GENERAL
        return counter.most_common(1)[0][0]


__all__ = ["ClinicalIntent", "ClinicalIntentTagger"]
