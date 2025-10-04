#!/usr/bin/env python3
"""Validate every configuration variant against the JSON Schema."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

import yaml

from Medical_KG.config.manager import ConfigError, ConfigSchemaValidator


def _load_mapping(path: Path) -> dict[str, object]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise ConfigError(f"{path.name} must contain a mapping at the root")
    return data


def _iter_config_paths(config_dir: Path) -> Iterable[Path]:
    yield from sorted(config_dir.glob("config*.yaml"))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "src" / "Medical_KG" / "config",
        help="Directory containing config.yaml, env overlays, and config.schema.json",
    )
    parser.add_argument(
        "--allow-older-schema",
        action="store_true",
        help="Allow configs to reference an older schema version",
    )
    color_group = parser.add_mutually_exclusive_group()
    color_group.add_argument("--color", dest="color", action="store_true", help="Force ANSI colour output")
    color_group.add_argument("--no-color", dest="color", action="store_false", help="Disable ANSI colour output")
    parser.set_defaults(color=sys.stdout.isatty())
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    config_dir = args.config_dir.resolve()
    schema_path = config_dir / "config.schema.json"
    if not schema_path.exists():
        print(f"Schema not found at {schema_path}", file=sys.stderr)
        return 2

    validator = ConfigSchemaValidator(schema_path, allow_older=args.allow_older_schema)
    validated = 0
    for path in _iter_config_paths(config_dir):
        payload = _load_mapping(path)
        try:
            validator.validate(payload, source=path.name, use_color=args.color)
        except ConfigError as exc:
            print(exc, file=sys.stderr)
            return 1
        validated += 1
        print(f"✓ {path.name}")

    print(f"Validated {validated} configuration payload(s) using schema v{validator.version}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
