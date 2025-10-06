from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Iterable

from langdetect import detect
from Medical_KG.ir.models import SpanMap

_DEHYPHENATION_DICTIONARY = {
    "treatment",
    "therapy",
    "monitoring",
    "sepsis",
    "lactate",
    "cardiovascular",
}


@dataclass(slots=True)
class NormalizedText:
    text: str
    raw_text: str
    span_map: SpanMap
    language: str


class TextNormalizer:
    """Canonicalizes text content while tracking span offsets."""

    def __init__(self, *, dictionary: Iterable[str] | None = None) -> None:
        self.dictionary = set(dictionary or _DEHYPHENATION_DICTIONARY)

    def normalize(self, text: str) -> NormalizedText:
        raw_text = text
        normalized = unicodedata.normalize("NFC", text)
        normalized = self._collapse_whitespace(normalized)
        normalized = self._dehyphenate(normalized)
        language = self._detect_language(normalized)
        span_map = SpanMap()
        span_map.add(0, len(raw_text), 0, len(normalized), "normalize")
        return NormalizedText(
            text=normalized, raw_text=raw_text, span_map=span_map, language=language
        )

    def _collapse_whitespace(self, text: str) -> str:
        normalized_lines = []
        for line in text.splitlines():
            normalized_lines.append(" ".join(line.split()))
        return "\n".join(normalized_lines)

    def _dehyphenate(self, text: str) -> str:
        pattern = re.compile(r"([A-Za-z]+)-\n([A-Za-z]+)")
        result: list[str] = []
        last_index = 0
        for match in pattern.finditer(text):
            result.append(text[last_index : match.start()])
            prefix, suffix = match.group(1), match.group(2)
            candidate = prefix + suffix
            if candidate.lower() in self.dictionary:
                result.append(candidate)
            else:
                result.append(f"{prefix}-{suffix}")
            last_index = match.end()
        result.append(text[last_index:])
        return "".join(result)

    def _detect_language(self, text: str) -> str:
        try:
            code = detect(text)
        except Exception:  # pragma: no cover - third-party failures
            return "unknown"
        return code[:2].lower()


def section_from_heading(heading: str, *, default: str = "other") -> str:
    heading_lower = heading.lower()
    if "introduction" in heading_lower:
        return "introduction"
    if "methods" in heading_lower:
        return "methods"
    if "results" in heading_lower:
        return "results"
    if "discussion" in heading_lower:
        return "discussion"
    return default
