"""NER helpers bridging optional scispaCy dependency."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from Medical_KG.utils.optional_dependencies import NLPPipeline, load_spacy_pipeline


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
        return [Mention(ent.text, ent.start_char, ent.end_char, ent.label_) for ent in doc.ents]


__all__ = ["Mention", "NerPipeline"]
