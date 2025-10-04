#!/usr/bin/env python3
"""Report direct ingestion pipeline usages that should migrate to streaming."""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable


RUN_ASYNC_PATTERN = re.compile(r"(?<!def\s)\brun_async(?:_legacy)?\(")


def iter_python_files(root: Path) -> Iterable[Path]:
    for path in root.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if any(part.startswith(".") for part in path.parts if part != "."):
            continue
        yield path


def find_usages(root: Path) -> list[tuple[Path, int, str]]:
    matches: list[tuple[Path, int, str]] = []
    for path in iter_python_files(root):
        content = path.read_text(encoding="utf-8")
        for match in RUN_ASYNC_PATTERN.finditer(content):
            line_number = content.count("\n", 0, match.start()) + 1
            line = content.splitlines()[line_number - 1].strip()
            matches.append((path, line_number, line))
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "root",
        nargs="?",
        default="src",
        help="Path to search (defaults to 'src').",
    )
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not root.exists():
        raise SystemExit(f"Path not found: {root}")
    matches = find_usages(root)
    if not matches:
        print("No eager pipeline usages found; streaming migration complete.")
        return 0
    print("Streaming migration suggestions:\n")
    for path, line_number, line in matches:
        print(f"- {path}:{line_number}: {line}")
        print(
            "  Consider switching to IngestionPipeline.stream_events() "
            "or iter_results() for incremental processing."
        )
    print(
        "\nLegacy run_async_legacy() support has been removed; update callers to use"
        " IngestionPipeline.stream_events() or run_async()."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
