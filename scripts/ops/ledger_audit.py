"""Audit ingestion ledger files for enum-only state usage.

This utility scans one or more ledger JSONL files and reports any occurrences
of removed legacy states or values that cannot be mapped to
``Medical_KG.ingestion.ledger.LedgerState``. The script is safe to run against
production snapshots and exits with a non-zero status when violations are
detected so it can be wired into release checklists.
"""

from __future__ import annotations

import argparse
import sys
import types
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import jsonlines

if "httpx" not in sys.modules:  # pragma: no cover - optional dependency shim
    try:
        import httpx  # type: ignore  # noqa: F401
    except ImportError:  # pragma: no cover - lightweight stub for CLIs
        httpx_module = types.ModuleType("httpx")

        class _AsyncClient:
            async def __aenter__(self) -> "_AsyncClient":
                return self

            async def __aexit__(self, *_exc: object) -> None:
                return None

            async def aclose(self) -> None:
                return None

        class _HTTPError(Exception):
            pass

        class _HTTPStatusError(_HTTPError):
            pass

        class _TimeoutException(Exception):
            pass

        class _Response:  # pragma: no cover - placeholder only
            pass

        class _Request:  # pragma: no cover - placeholder only
            pass

        httpx_module.AsyncClient = _AsyncClient
        httpx_module.MockTransport = object
        httpx_module.TimeoutException = _TimeoutException
        httpx_module.HTTPError = _HTTPError
        httpx_module.HTTPStatusError = _HTTPStatusError
        httpx_module.Response = _Response
        httpx_module.Request = _Request
        sys.modules["httpx"] = httpx_module

from Medical_KG.ingestion.ledger import (
    LedgerState,
    _PERSISTED_STATE_ALIASES,
)


class LegacyStateDetected(RuntimeError):
    """Raised when a removed legacy state marker is encountered."""


@dataclass
class AuditFinding:
    path: Path
    line: int
    message: str

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.path}:{self.line}: {self.message}"


def _coerce_state(raw: object, *, context: str) -> LedgerState:
    if isinstance(raw, LedgerState):
        return raw
    if isinstance(raw, str):
        token = raw.strip()
        if not token:
            raise ValueError(f"{context} is blank")
        alias = _PERSISTED_STATE_ALIASES.get(token.lower())
        if alias is not None:
            return alias
        try:
            return LedgerState[token.upper()]
        except KeyError:
            lower = token.lower()
            if lower == "legacy":
                raise LegacyStateDetected(
                    f"{context} references removed legacy state"
                )
            try:
                return LedgerState(lower)
            except ValueError as exc:
                raise ValueError(f"{context} contains unknown state {token!r}") from exc
    raise TypeError(f"{context} is not a valid ledger state type: {type(raw)!r}")


def audit_ledger(path: Path) -> tuple[Counter[str], list[AuditFinding]]:
    counts: Counter[str] = Counter()
    findings: list[AuditFinding] = []
    with jsonlines.open(path, mode="r") as reader:
        for index, row in enumerate(reader, start=1):
            if not isinstance(row, dict):
                findings.append(
                    AuditFinding(path=path, line=index, message="row is not a mapping")
                )
                continue
            try:
                new_state = _coerce_state(row.get("new_state"), context="new_state")
                old_state = _coerce_state(row.get("old_state"), context="old_state")
            except LegacyStateDetected as exc:
                findings.append(AuditFinding(path=path, line=index, message=str(exc)))
                continue
            except (TypeError, ValueError) as exc:
                findings.append(AuditFinding(path=path, line=index, message=str(exc)))
                continue
            counts[new_state.name] += 1
            counts[old_state.name] += 1
    return counts, findings


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "ledgers",
        metavar="LEDGER",
        type=Path,
        nargs="+",
        help="Path(s) to ledger JSONL files",
    )
    parser.add_argument(
        "--fail-on-warnings",
        action="store_true",
        help="Treat unknown/legacy states as fatal (default when multiple findings)",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    overall_counts: Counter[str] = Counter()
    all_findings: list[AuditFinding] = []
    for ledger_path in args.ledgers:
        counts, findings = audit_ledger(ledger_path)
        overall_counts.update(counts)
        all_findings.extend(findings)
        print(f"Ledger {ledger_path}:")
        if counts:
            for state, total in sorted(counts.items()):
                print(f"  {state:<12} {total}")
        else:
            print("  (no states recorded)")
        if findings:
            print("  Issues:")
            for finding in findings:
                print(f"    - {finding}")

    if len(args.ledgers) > 1:
        print("\nAggregate state counts:")
        for state, total in sorted(overall_counts.items()):
            print(f"  {state:<12} {total}")

    if all_findings:
        print(
            f"\nDetected {len(all_findings)} issue(s); run compaction before deployment."
        )
        return 1
    if args.fail_on_warnings and all_findings:
        return 1
    print("\nNo legacy states detected; ledger entries are enum-only.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
