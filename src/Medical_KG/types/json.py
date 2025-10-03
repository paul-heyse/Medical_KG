"""Shared JSON-compatible type aliases used across the codebase."""

from __future__ import annotations

from typing import Mapping, MutableMapping, TypeAlias

JSONPrimitive: TypeAlias = str | int | float | bool | None
JSONValue: TypeAlias = JSONPrimitive | list["JSONValue"] | dict[str, "JSONValue"]
JSONObject: TypeAlias = dict[str, JSONValue]
JSONMapping: TypeAlias = Mapping[str, JSONValue]
MutableJSONMapping: TypeAlias = MutableMapping[str, JSONValue]

__all__ = [
    "JSONPrimitive",
    "JSONValue",
    "JSONObject",
    "JSONMapping",
    "MutableJSONMapping",
]
