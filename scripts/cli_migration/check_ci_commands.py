#!/usr/bin/env python3
"""Scan CI/workflow files for legacy ingestion CLI invocations."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

LEGACY_TOKENS = {
    "med-ingest": "med ingest",
    "--continue-from-ledger": "--resume",
    "--batch-file": "--batch",
    "--max-records": "--limit",
}

DEFAULT_GLOBS = (".github/workflows/*.yml", "ops/**/*.sh", "ops/**/*.yml", "scripts/**/*.sh")


@dataclass(slots=True)
class Finding:
    path: str
    line: int
    legacy: str
    replacement: str


def iter_files(root: Path, globs: Iterable[str]) -> Iterable[Path]:
    for pattern in globs:
        yield from root.glob(pattern)


def scan_file(path: Path) -> list[Finding]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    findings: list[Finding] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        for legacy, replacement in LEGACY_TOKENS.items():
            if legacy in line:
                findings.append(
                    Finding(path=str(path), line=line_no, legacy=legacy, replacement=replacement)
                )
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd(), help="Repository root to scan")
    parser.add_argument("--json", action="store_true", help="Emit JSON report")
    parser.add_argument(
        "--include",
        nargs="*",
        default=list(DEFAULT_GLOBS),
        help="Glob patterns to scan (defaults target CI & ops directories)",
    )
    args = parser.parse_args(argv)

    findings = [finding for path in iter_files(args.root, args.include) for finding in scan_file(path)]

    if args.json:
        payload = {"findings": [asdict(item) for item in findings], "legacy_count": len(findings)}
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if not findings:
            print("No legacy ingestion commands detected.")
        else:
            print("Legacy ingestion commands detected:\n")
            for finding in findings:
                print(
                    f"- {finding.path}:{finding.line}: '{finding.legacy}' → consider '{finding.replacement}'",
                )
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
