"""Deterministic identifier detectors and validators."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List


@dataclass(slots=True)
class IdentifierCandidate:
    scheme: str
    code: str
    confidence: float
    start: int
    end: int


class DeterministicDetectors:
    RXCUI = re.compile(r"\b(\d{4,7})\b")
    UNII = re.compile(r"\b([A-Z0-9]{10})\b")
    LOINC = re.compile(r"\b(\d{1,7}-\d)\b")
    NCT = re.compile(r"\b(NCT\d{8})\b", re.IGNORECASE)
    GTIN = re.compile(r"\b(\d{14})\b")

    @staticmethod
    def _mod10(code: str) -> bool:
        total = 0
        reverse = code[::-1]
        for index, digit in enumerate(reverse):
            n = int(digit)
            if index % 2 == 1:
                n *= 3
            total += n
        return total % 10 == 0

    def detect(self, text: str) -> List[IdentifierCandidate]:
        candidates: List[IdentifierCandidate] = []
        for match in self.RXCUI.finditer(text):
            start, end = match.span()
            candidates.append(IdentifierCandidate("RxCUI", match.group(1), 1.0, start, end))
        for match in self.UNII.finditer(text):
            start, end = match.span()
            candidates.append(IdentifierCandidate("UNII", match.group(1), 1.0, start, end))
        for match in self.LOINC.finditer(text):
            start, end = match.span()
            candidates.append(IdentifierCandidate("LOINC", match.group(1), 1.0, start, end))
        for match in self.NCT.finditer(text):
            start, end = match.span()
            candidates.append(IdentifierCandidate("NCT", match.group(1).upper(), 1.0, start, end))
        for match in self.GTIN.finditer(text):
            if not self._mod10(match.group(1)):
                continue
            start, end = match.span()
            candidates.append(IdentifierCandidate("GTIN-14", match.group(1), 1.0, start, end))
        return candidates


__all__ = ["IdentifierCandidate", "DeterministicDetectors"]
