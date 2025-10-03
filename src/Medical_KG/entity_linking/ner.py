"""NER helpers bridging optional scispaCy dependency."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from Medical_KG.compat import PipelineProtocol, load_pipeline


@dataclass(slots=True)
class Mention:
    text: str
    start: int
    end: int
    label: str


class NerPipeline:
    """Thin wrapper around spaCy pipelines with typed fallbacks."""

    def __init__(self, model: str = "en_core_sci_sm") -> None:
        try:
            self._nlp: PipelineProtocol | None = load_pipeline(model)
        except Exception:  # pragma: no cover - defensive
            self._nlp = None

    def __call__(self, text: str) -> Sequence[Mention]:
        pipeline = self._nlp
        if pipeline is None:
            return []
        doc = pipeline(text)
        return [Mention(ent.text, ent.start_char, ent.end_char, ent.label_) for ent in doc.ents]


__all__ = ["Mention", "NerPipeline"]
