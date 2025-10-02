"""Rule-based intent routing for retrieval requests."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping


@dataclass(frozen=True)
class IntentRule:
    name: str
    keywords: tuple[re.Pattern[str], ...]
    boosts: Mapping[str, float]
    filters: Mapping[str, object]


class IntentClassifier:
    """Lightweight classifier driven by regex rules with fallback to general."""

    def __init__(self, rules: Iterable[IntentRule], default: str = "general") -> None:
        self._rules = list(rules)
        self._default = default

    def detect(self, query: str) -> str:
        lowered = query.lower()
        for rule in self._rules:
            if any(pattern.search(lowered) for pattern in rule.keywords):
                return rule.name
        return self._default

    def context_for(self, intent: str) -> tuple[Mapping[str, float], Mapping[str, object]]:
        for rule in self._rules:
            if rule.name == intent:
                return rule.boosts, rule.filters
        for rule in self._rules:
            if rule.name == self._default:
                return rule.boosts, rule.filters
        return {}, {}


__all__ = ["IntentClassifier", "IntentRule"]
