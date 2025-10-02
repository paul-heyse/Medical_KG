"""Licensing enforcement utilities."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import yaml


@dataclass(frozen=True, slots=True)
class LicenseTier:
    name: str
    can_access: Mapping[str, bool]


@dataclass(frozen=True, slots=True)
class LicenseEntry:
    vocab: str
    licensed: bool
    territory: str | None


class LicenseRegistry:
    """Loads and validates license entitlements from licenses.yml."""

    def __init__(self, entries: Mapping[str, LicenseEntry], tiers: Mapping[str, LicenseTier]) -> None:
        self._entries = entries
        self._tiers = tiers

    @classmethod
    def from_yaml(cls, path: Path) -> "LicenseRegistry":
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        vocabs = data.get("vocabs", {})
        tiers = data.get("tiers", {})
        entries = {
            vocab.upper(): LicenseEntry(vocab=vocab.upper(), licensed=bool(info.get("licensed")), territory=info.get("territory"))
            for vocab, info in vocabs.items()
        }
        tier_objects = {
            name: LicenseTier(name=name, can_access={k.upper(): bool(v) for k, v in config.items()})
            for name, config in tiers.items()
        }
        return cls(entries, tier_objects)

    def require(self, vocab: str) -> None:
        entry = self._entries.get(vocab.upper())
        if entry is None or not entry.licensed:
            raise PermissionError(f"Vocabulary {vocab} is not licensed")

    def filter_labels(self, vocab: str, tier: str, label: str) -> str:
        entry = self._entries.get(vocab.upper())
        tier_entry = self._tiers.get(tier.lower())
        if entry is None:
            return "[unavailable]"
        if not entry.licensed:
            return "[license required]"
        if tier_entry and not tier_entry.can_access.get(vocab.upper(), True):
            return f"[{tier} tier cannot access {vocab}]"
        return label


__all__ = ["LicenseRegistry", "LicenseTier"]
