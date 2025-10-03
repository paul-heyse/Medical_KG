"""Quality gates for MinerU output."""
from __future__ import annotations

import string
from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .postprocess import TextBlock


@dataclass(slots=True)
class QaMetrics:
    reading_order_score: float
    ocr_confidence_mean: float
    table_count: int
    header_footer_suppressed: int


class QaGateError(RuntimeError):
    pass


class QaGates:
    def __init__(
        self,
        *,
        reading_order_threshold: float = 0.85,
        ocr_threshold: float = 0.8,
        min_pages: int = 1,
        max_pages: int = 200,
        allowed_languages: Sequence[str] = ("en",),
    ) -> None:
        self._reading_order_threshold = reading_order_threshold
        self._ocr_threshold = ocr_threshold
        self._min_pages = min_pages
        self._max_pages = max_pages
        self._allowed_languages = tuple(allowed_languages)

    def reading_order(self, blocks: Sequence[TextBlock]) -> float:
        if not blocks:
            return 1.0
        in_order = 0
        for earlier, later in zip(blocks, blocks[1:]):
            if earlier.page < later.page or (earlier.page == later.page and earlier.y <= later.y):
                in_order += 1
        return in_order / max(1, len(blocks) - 1)

    def ocr_quality(self, confidences: Sequence[float]) -> float:
        if not confidences:
            return 1.0
        return sum(confidences) / len(confidences)

    def tables_valid(self, tables: Sequence[Mapping[str, object]]) -> bool:
        for table in tables:
            rows = table.get("rows")
            if isinstance(rows, list) and rows and all(isinstance(row, list) and len(row) >= 2 for row in rows):
                return True
        return False

    def evaluate(
        self,
        *,
        blocks: Sequence[TextBlock],
        confidences: Sequence[float],
        tables: Sequence[Mapping[str, object]],
        page_count: int | None = None,
        language: str | None = None,
    ) -> QaMetrics:
        reading_score = self.reading_order(blocks)
        if reading_score < self._reading_order_threshold:
            raise QaGateError("Reading order sanity check failed")
        ocr_score = self.ocr_quality(confidences)
        if ocr_score < self._ocr_threshold:
            raise QaGateError("OCR confidence below threshold")
        if tables and not self.tables_valid(tables):
            raise QaGateError("Table rectangularization failed")
        if page_count is not None:
            if page_count < self._min_pages:
                raise QaGateError("PDF shorter than minimum page requirement")
            if page_count > self._max_pages:
                raise QaGateError("PDF exceeds maximum page limit")
        detected_language = language or self.detect_language("\n".join(block.text for block in blocks))
        if self._allowed_languages and detected_language not in self._allowed_languages:
            raise QaGateError(f"Unsupported language: {detected_language}")
        suppressed = len(blocks) - len({block.text for block in blocks})
        return QaMetrics(
            reading_order_score=reading_score,
            ocr_confidence_mean=ocr_score,
            table_count=len(tables),
            header_footer_suppressed=max(0, suppressed),
        )

    def detect_language(self, text: str) -> str:
        letters = [char for char in text if char.isalpha()]
        if not letters:
            return "unknown"
        ascii_letters = sum(1 for char in letters if char in string.ascii_letters)
        ratio = ascii_letters / len(letters)
        return "en" if ratio >= 0.6 else "non-en"


__all__ = ["QaGates", "QaGateError", "QaMetrics"]
