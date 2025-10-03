"""NER helpers bridging optional scispaCy dependency."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Sequence


@dataclass(slots=True)
class Mention:
    text: str
    start: int
    end: int
    label: str


class NerPipeline:
    def __init__(self, model: str = "en_core_sci_sm") -> None:
        try:  # pragma: no cover - optional heavy dependency
            import spacy
        except ModuleNotFoundError:  # pragma: no cover - tests may run without spaCy
            spacy = None

    def __call__(self, text: str) -> Sequence[Mention]:
        if self._nlp is None:
            return []
        doc = self._nlp(text)
        return [Mention(ent.text, ent.start_char, ent.end_char, ent.label_) for ent in doc.ents]


__all__ = ["Mention", "NerPipeline"]
