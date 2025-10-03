"""Minimal YAML shim backed by JSON parsing."""

from __future__ import annotations

import json
from typing import Any


def safe_load(stream: Any) -> Any:
    if hasattr(stream, "read"):
        text = stream.read()
    else:
        text = stream
    if text is None or text == "":
        return {}
    text = str(text)
    if text.lstrip().startswith("{"):
        return json.loads(text)
    return _parse_simple_yaml(text)


def safe_dump(data: Any, *, sort_keys: bool = False) -> str:
    return json.dumps(data, indent=2, sort_keys=sort_keys)


def _parse_simple_yaml(text: str) -> Any:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.strip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip())
        key, _, remainder = raw_line.partition(":")
        key = key.strip()
        value = remainder.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if value:
            parent[key] = _parse_scalar(value)
        else:
            new_map: dict[str, Any] = {}
            parent[key] = new_map
            stack.append((indent, new_map))
    return root


def _parse_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


__all__ = ["safe_load", "safe_dump"]
