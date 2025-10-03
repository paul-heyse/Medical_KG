"""Medical-specific post-processing on MinerU output."""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List, Mapping, MutableMapping, Sequence


@dataclass(slots=True)
class TextBlock:
    page: int
    y: float
    text: str
    label: str | None = None


class TwoColumnReflow:
    def detect_columns(self, blocks: Sequence[TextBlock]) -> bool:
        buckets = Counter(int(block.y // 100) for block in blocks if block.text.strip())
        if not buckets:
            return False
        return max(buckets.values()) / max(1, len(blocks)) > 0.6

    def reflow(self, blocks: Sequence[TextBlock]) -> List[TextBlock]:
        if not blocks:
            return []
        left, right = [], []
        for block in blocks:
            if block.y < 300:
                left.append(block)
            else:
                right.append(block)
        ordered = sorted(left, key=lambda b: (b.page, b.y)) + sorted(right, key=lambda b: (b.page, b.y))
        return ordered


class HeaderFooterSuppressor:
    def suppress(self, blocks: Sequence[TextBlock]) -> List[TextBlock]:
        occurrences: MutableMapping[str, int] = Counter(block.text.strip() for block in blocks if block.text.strip())
        threshold = max(1, int(0.6 * len({block.page for block in blocks})))
        filtered = [block for block in blocks if occurrences[block.text.strip()] <= threshold]
        return filtered


class HyphenationRepair:
    def repair(self, text: str) -> str:
        return text.replace("-\n", "")


class EquationNormaliser:
    """Normalise LaTeX-style inline equations to a consistent format."""

    _inline_pattern = re.compile(r"\$(.+?)\$")

    def normalise(self, text: str) -> str:
        def _cleanup(match: re.Match[str]) -> str:
            content = re.sub(r"\s+", " ", match.group(1).strip())
            return f"$ {content} $"

        return re.sub(self._inline_pattern, _cleanup, text)


class SectionLabeler:
    SECTIONS = {
        "introduction": "introduction",
        "methods": "methods",
        "results": "results",
        "discussion": "discussion",
    }

    def label(self, blocks: Sequence[TextBlock]) -> List[TextBlock]:
        labeled = []
        current = None
        for block in blocks:
            heading = block.text.lower().strip()
            if heading in self.SECTIONS:
                current = self.SECTIONS[heading]
                labeled.append(TextBlock(page=block.page, y=block.y, text=block.text, label=current))
            else:
                labeled.append(TextBlock(page=block.page, y=block.y, text=block.text, label=current))
        return labeled


class ReferenceExtractor:
    """Extract simple reference entries from labeled text blocks."""

    _reference_marker = re.compile(r"^(\d+)[.\]]\s+(.*)")

    def extract(self, blocks: Sequence[TextBlock]) -> List[dict[str, str]]:
        references: List[dict[str, str]] = []
        in_reference_section = False
        for block in blocks:
            text = block.text.strip()
            if not text:
                continue
            if text.lower().startswith("references"):
                in_reference_section = True
                continue
            if not in_reference_section:
                continue
            match = self._reference_marker.match(text)
            if match:
                references.append({"index": match.group(1), "citation": match.group(2)})
        return references


class FigureCaptionExtractor:
    """Identify figure captions and associate them with figure numbers."""

    _figure_pattern = re.compile(r"^figure\s+(\d+)[.:]\s*(.+)$", re.IGNORECASE)

    def extract(self, blocks: Sequence[TextBlock]) -> List[dict[str, str]]:
        captions: List[dict[str, str]] = []
        for block in blocks:
            text = block.text.strip()
            if not text:
                continue
            match = self._figure_pattern.match(text)
            if match:
                captions.append({"figure": match.group(1), "caption": match.group(2)})
        return captions


__all__ = [
    "TextBlock",
    "TwoColumnReflow",
    "HeaderFooterSuppressor",
    "HyphenationRepair",
    "EquationNormaliser",
    "SectionLabeler",
    "ReferenceExtractor",
    "FigureCaptionExtractor",
]
