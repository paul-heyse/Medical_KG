"""Shared type aliases for catalog ingestion and indexing payloads."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TypeAlias

JsonScalar: TypeAlias = str | int | float | bool | None
JsonValue: TypeAlias = JsonScalar | Sequence["JsonValue"] | Mapping[str, "JsonValue"]
AuditMetadata: TypeAlias = Mapping[str, JsonValue]

__all__ = ["AuditMetadata", "JsonScalar", "JsonValue"]
