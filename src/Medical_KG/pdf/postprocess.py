"""Medical-specific post-processing on MinerU output."""
from __future__ import annotations

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


__all__ = [
    "TextBlock",
    "TwoColumnReflow",
    "HeaderFooterSuppressor",
    "HyphenationRepair",
    "SectionLabeler",
]
