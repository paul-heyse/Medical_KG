"""SPLADE-style sparse expansion implemented with lightweight heuristics."""
from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Sequence

_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9]+")


@dataclass(slots=True)
class SPLADEExpander:
    """Approximate SPLADE expansion using token statistics."""

    top_k: int = 400
    min_weight: float = 0.05

    def expand(self, texts: Sequence[str]) -> List[Dict[str, float]]:
        expansions: List[Dict[str, float]] = []
        for text in texts:
            tokens = [token.lower() for token in _TOKEN_PATTERN.findall(text)]
            counts = Counter(tokens)
            if not counts:
                expansions.append({})
                continue
            weighted = {token: 1.0 + math.log(count) for token, count in counts.items()}
            norm = math.sqrt(sum(value * value for value in weighted.values())) or 1.0
            scaled = {token: value / norm for token, value in weighted.items()}
            filtered = {token: value for token, value in scaled.items() if value >= self.min_weight}
            top_terms = dict(sorted(filtered.items(), key=lambda item: item[1], reverse=True)[: self.top_k])
            expansions.append(top_terms)
        return expansions


__all__ = ["SPLADEExpander"]
