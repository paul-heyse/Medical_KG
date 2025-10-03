from __future__ import annotations

import ast
import os
import sys
import threading
from collections import defaultdict
from pathlib import Path
from trace import Trace

import pytest

@pytest.fixture
def monkeypatch_fixture(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    return monkeypatch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PACKAGE_ROOT = SRC / "Medical_KG"
TARGET_COVERAGE = float(os.environ.get("COVERAGE_TARGET", "0.95"))

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

_TRACE = Trace(count=True, trace=False)

def _activate_tracing() -> None:  # pragma: no cover - instrumentation only
    sys.settrace(_TRACE.globaltrace)
    threading.settrace(_TRACE.globaltrace)


if os.environ.get("DISABLE_COVERAGE_TRACE") != "1":
    _activate_tracing()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:  # pragma: no cover - instrumentation only
    sys.settrace(None)
    threading.settrace(None)
    if os.environ.get("DISABLE_COVERAGE_TRACE") == "1":
        return
    results = _TRACE.results()
    executed: dict[Path, set[int]] = defaultdict(set)
    for (filename, lineno), count in results.counts.items():
        if count <= 0:
            continue
        path = Path(filename)
        try:
            path = path.resolve()
        except OSError:
            continue
        if PACKAGE_ROOT not in path.parents and path != PACKAGE_ROOT:
            continue
        executed[path].add(lineno)

    missing: dict[Path, set[int]] = {}
    per_file_coverage: list[tuple[Path, float]] = []
    total_statements = 0
    total_covered = 0

    for py_file in PACKAGE_ROOT.rglob("*.py"):
        statements = _statement_lines(py_file)
        if not statements:
            continue
        executed_lines = executed.get(py_file.resolve(), set())
        covered = statements & executed_lines
        uncovered = statements - covered
        rel_path = py_file.relative_to(ROOT)
        per_file_coverage.append(
            (
                rel_path,
                len(covered) / len(statements) if statements else 1.0,
            )
        )
        total_statements += len(statements)
        total_covered += len(covered)
        if uncovered:
            missing[rel_path] = uncovered

    overall = total_covered / total_statements if total_statements else 1.0

    if missing:
        details = "; ".join(
            f"{path}:{','.join(str(line) for line in sorted(lines))}" for path, lines in sorted(missing.items())
        )
        (ROOT / "coverage_missing.txt").write_text(details, encoding="utf-8")
    else:
        coverage_file = ROOT / "coverage_missing.txt"
        if coverage_file.exists():
            coverage_file.unlink()

    if overall + 1e-9 < TARGET_COVERAGE:
        lowest = sorted(per_file_coverage, key=lambda item: item[1])[:5]
        summary = ", ".join(f"{path}={pct:.1%}" for path, pct in lowest)
        pytest.fail(
            f"Statement coverage {overall:.1%} below target {TARGET_COVERAGE:.0%}. "
            f"Lowest files: {summary}"
        )


def _statement_lines(path: Path) -> set[int]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt):
            lines.add(node.lineno)
    return lines
