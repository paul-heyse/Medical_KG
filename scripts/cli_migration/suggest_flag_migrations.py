#!/usr/bin/env python3
"""Suggest unified CLI replacements for legacy ingestion commands."""

from __future__ import annotations

import argparse
import json
import shlex
import sys
from typing import Sequence

from Medical_KG.cli import _translate_legacy_args


def translate(command: Sequence[str]) -> dict[str, object]:
    translated, used = _translate_legacy_args(list(command))
    return {
        "input": list(command),
        "suggested": translated or [],
        "used_legacy_flags": used,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        nargs=argparse.REMAINDER,
        help="Legacy command to translate. If omitted, read from stdin (one command per line).",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable output")
    args = parser.parse_args(argv)

    commands: list[list[str]] = []
    if args.command:
        commands.append(args.command)
    else:
        for raw in (line.strip() for line in sys.stdin if line.strip()):
            commands.append(shlex.split(raw))

    results = [translate(command) for command in commands]

    if args.json:
        json.dump({"results": results}, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        for payload in results:
            legacy = " ".join(payload["input"])
            suggested = " ".join(payload["suggested"]) or "<no translation>"
            marker = "(legacy flags detected)" if payload["used_legacy_flags"] else ""
            print(f"{legacy} -> {suggested} {marker}".strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
