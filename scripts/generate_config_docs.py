#!/usr/bin/env python3
"""Generate Markdown reference docs from config.schema.json."""
from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "src" / "Medical_KG" / "config" / "config.schema.json",
        help="Path to the JSON Schema file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional path to write the generated Markdown",
    )
    return parser.parse_args()


def _describe_type(schema: Mapping[str, Any]) -> str:
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return ", ".join(str(item) for item in schema_type)
    return str(schema_type) if schema_type else "any"


def _extract_description(schema: Mapping[str, Any]) -> str | None:
    description = schema.get("description")
    if isinstance(description, str) and description.strip():
        return description.strip()
    return None


def _render_properties(schema: Mapping[str, Any], path: str, depth: int, lines: list[str]) -> None:
    properties = schema.get("properties")
    if not isinstance(properties, Mapping):
        return
    required = set(schema.get("required", []))
    for name, subschema in sorted(properties.items()):
        if not isinstance(subschema, Mapping):
            continue
        header = "#" * depth + f" `{path + name if path else name}`"
        lines.append(header)
        lines.append("")
        details: list[str] = []
        details.append(f"- **Type**: {_describe_type(subschema)}")
        if name in required:
            details.append("- **Required**: yes")
        else:
            details.append("- **Required**: no")
        if enum := subschema.get("enum"):
            details.append(f"- **Enum**: {', '.join(map(str, enum))}")
        if fmt := subschema.get("format"):
            details.append(f"- **Format**: {fmt}")
        if default := subschema.get("default"):
            details.append(f"- **Default**: {default}")
        description = _extract_description(subschema)
        if description:
            details.append(f"- **Description**: {description}")
        lines.extend(details)
        lines.append("")
        next_path = f"{path}{name}."
        _render_properties(subschema, next_path, depth + 1, lines)
        if subschema.get("items") and isinstance(subschema["items"], Mapping):
            item_schema = subschema["items"]
            lines.append("- **Items**:")
            nested_description = _extract_description(item_schema)
            item_type = _describe_type(item_schema)
            lines.append(f"  - type: {item_type}")
            if nested_description:
                lines.append(f"  - description: {nested_description}")
            lines.append("")


def main() -> int:
    args = parse_args()
    schema = json.loads(args.schema.read_text(encoding="utf-8"))
    if not isinstance(schema, Mapping):
        raise SystemExit("Schema root must be an object")

    version = schema.get("version", "unknown")
    lines: list[str] = [
        "# Configuration Schema Reference",
        "",
        f"Generated from `config.schema.json` version `{version}`.",
        "",
        "This file is generated via `scripts/generate_config_docs.py`. Do not edit manually.",
        "",
    ]
    _render_properties(schema, path="", depth=2, lines=lines)
    output = "\n".join(lines).rstrip() + "\n"

    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        print(output)
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
