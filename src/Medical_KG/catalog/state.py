"""State management helpers for catalog releases."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(slots=True)
class CatalogStateStore:
    """In-memory record of catalog release hashes and ontology versions."""

    _release_hash: str | None = None
    _release_versions: dict[str, str] = field(default_factory=dict)

    def get_release_hash(self) -> str | None:
        return self._release_hash

    def set_release_hash(self, value: str) -> None:
        self._release_hash = value

    def get_release_versions(self) -> dict[str, str]:
        return dict(self._release_versions)

    def set_release_versions(self, versions: Mapping[str, str]) -> None:
        self._release_versions = {key: str(value) for key, value in versions.items()}


__all__ = ["CatalogStateStore"]
