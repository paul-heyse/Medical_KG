"""Minimal YAML shim backed by JSON parsing."""

from __future__ import annotations

import json
from typing import Any


def safe_load(stream: Any) -> Any:
    """Parse a tiny YAML subset into native Python values."""

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
    """Serialize Python values using JSON for deterministic output."""

    return json.dumps(data, indent=2, sort_keys=sort_keys)


def _parse_simple_yaml(text: str) -> Any:
    lines: list[tuple[int, str]] = []
    for raw_line in text.splitlines():
        stripped = _strip_comment(raw_line)
        if not stripped.strip():
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        lines.append((indent, stripped.strip()))

    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]

    for index, (indent, content) in enumerate(lines):
        while len(stack) > 1 and indent <= stack[-1][0]:
            stack.pop()

        parent = stack[-1][1]
        next_line = lines[index + 1] if index + 1 < len(lines) else None

        if content.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError("Encountered list item without list parent")
            item_text = content[2:].strip()
            if not item_text:
                container = _container_for_next(indent, next_line)
                parent.append(container)
                stack.append((indent, container))
                continue
            parent.append(_parse_scalar(item_text))
            continue

        key, _, remainder = content.partition(":")
        key = key.strip()
        value_text = remainder.strip()
        if not isinstance(parent, dict):
            raise ValueError("Mapping entry requires dict parent")
        if value_text:
            parent[key] = _parse_scalar(value_text)
            continue

        container = _container_for_next(indent, next_line)
        parent[key] = container
        stack.append((indent, container))

    return root


def _container_for_next(indent: int, next_line: tuple[int, str] | None) -> Any:
    if next_line is None:
        return {}
    next_indent, next_content = next_line
    if next_indent <= indent:
        return {}
    if next_content.startswith("- "):
        return []
    return {}


def _strip_comment(raw_line: str) -> str:
    result: list[str] = []
    in_single = False
    in_double = False
    iterator = iter(enumerate(raw_line))
    for index, char in iterator:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char == "#" and not in_single and not in_double:
            return "".join(result)
        result.append(char)
    return "".join(result)


def _parse_scalar(value: str) -> Any:
    if value.startswith("'") and value.endswith("'"):
        return value[1:-1].replace("''", "'")
    if value.startswith('"') and value.endswith('"'):
        unescaped = value[1:-1].replace("\\\"", '"').replace("\\\\", "\\")
        return unescaped
    lowered = value.lower()
    if lowered in {"true", "false"}:
        return lowered == "true"
    if lowered in {"null", "none", "~"}:
        return None
    if value.startswith("[") and value.endswith("]"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    if value.startswith("{") and value.endswith("}"):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            pass
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value


__all__ = ["safe_load", "safe_dump"]
