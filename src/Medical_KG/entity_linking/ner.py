"""NER helpers bridging optional scispaCy dependency."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Sequence

from Medical_KG.utils.optional_dependencies import NLPPipeline, load_spacy_pipeline

_ABBREVIATIONS: Dict[str, str] = {"mi": "myocardial infarction"}


@dataclass(slots=True)
class Mention:
    text: str
    start: int
    end: int
    label: str


class NerPipeline:
    """Thin wrapper around spaCy pipelines with typed fallbacks."""

    def __init__(self, model: str = "en_core_sci_sm") -> None:
        self._nlp: NLPPipeline | None = load_spacy_pipeline(model)

    def __call__(self, text: str) -> Sequence[Mention]:
        if self._nlp is None:
            return []
        doc = self._nlp(text)
        mentions: list[Mention] = []
        for ent in doc.ents:
            raw_text = ent.text
            normalized = _ABBREVIATIONS.get(raw_text.lower(), raw_text)
            mention = Mention(normalized, ent.start_char, ent.end_char, ent.label_)
            # Skip negated entities (simple heuristic)
            prefix = text[: mention.start].lower()
            if re.search(r"\b(no|without)\b\s*$", prefix):
                continue
            replaced = False
            for idx, existing in enumerate(mentions):
                overlaps = not (mention.end <= existing.start or mention.start >= existing.end)
                if overlaps:
                    if (mention.end - mention.start) > (existing.end - existing.start):
                        mentions[idx] = mention
                    replaced = True
                    break
            if not replaced:
                mentions.append(mention)
        return mentions


__all__ = ["Mention", "NerPipeline"]
