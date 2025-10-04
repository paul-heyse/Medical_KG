"""Lightweight clinical intent tagging based on heuristics."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Mapping, Sequence

from Medical_KG.embeddings import QwenEmbeddingClient


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
class EmbeddingIntentClassifier:
    """Lightweight classifier using hashed embeddings and weak supervision weights."""

    client: QwenEmbeddingClient = field(
        default_factory=lambda: QwenEmbeddingClient(dimension=32, batch_size=32)
    )
    weights: Mapping[ClinicalIntent, List[str]] = field(
        default_factory=lambda: {
            ClinicalIntent.PICO_OUTCOME: ["outcome", "response", "survival"],
            ClinicalIntent.ADVERSE_EVENT: ["adverse", "toxicity", "serious"],
            ClinicalIntent.PICO_INTERVENTION: ["dose", "treated", "administered"],
            ClinicalIntent.PICO_POPULATION: ["patients", "subjects", "adults"],
        }
    )

    def predict(self, sentence: str) -> ClinicalIntent | None:
        embeddings = self.client.embed([sentence, sentence[::-1]])
        scores: dict[ClinicalIntent, float] = {}
        for intent, cues in self.weights.items():
            score = sum(1.0 for cue in cues if cue in sentence.lower())
            score += sum(value for value in embeddings[0][:4])
            score -= sum(value for value in embeddings[1][:4])
            scores[intent] = score
        best_intent, best_score = max(scores.items(), key=lambda item: item[1])
        if best_score > 0.5:
            return best_intent
        return None


@dataclass(slots=True)
class ClinicalIntentTagger:
    """Hybrid heuristic and embedding-backed intent tagger."""

    classifier: EmbeddingIntentClassifier = field(default_factory=EmbeddingIntentClassifier)

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
        guess = self.classifier.predict(sentence)
        if guess:
            return guess
        return ClinicalIntent.GENERAL

    def tag_sentences(
        self, sentences: Sequence[str], *, sections: Sequence[str | None] | None = None
    ) -> List[ClinicalIntent]:
        intents: List[ClinicalIntent] = []
        section_sequence = list(sections) if sections is not None else [None] * len(sentences)
        for sentence, section in zip(sentences, section_sequence):
            intents.append(self.tag_sentence(sentence, section=section))
        return intents

    def dominant_intent(self, intents: Iterable[ClinicalIntent]) -> ClinicalIntent:
        counter = Counter(intents)
        if not counter:
            return ClinicalIntent.GENERAL
        return counter.most_common(1)[0][0]


__all__ = ["ClinicalIntent", "ClinicalIntentTagger"]
