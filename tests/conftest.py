from __future__ import annotations

import ast
import json
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
BUDGET_PATH = ROOT / "coverage_budget.json"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

_TRACE = Trace(count=True, trace=False)
if BUDGET_PATH.exists():
    BUDGETS = json.loads(BUDGET_PATH.read_text(encoding="utf-8"))
else:
    BUDGETS = {}


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
    for py_file in PACKAGE_ROOT.rglob("*.py"):
        statements = _statement_lines(py_file)
        if not statements:
            continue
        executed_lines = executed.get(py_file.resolve(), set())
        uncovered = statements - executed_lines
        rel_path = py_file.relative_to(ROOT)
        allowed = set(BUDGETS.get(str(rel_path), []))
        extra = uncovered - allowed
        if extra:
            missing[rel_path] = extra

    if missing:
        details = "; ".join(
            f"{path}:{','.join(str(line) for line in sorted(lines))}" for path, lines in sorted(missing.items())
        )
        (ROOT / "coverage_missing.txt").write_text(details, encoding="utf-8")
        pytest.fail(f"Coverage below 100% for: {details}")


def _statement_lines(path: Path) -> set[int]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt):
            lines.add(node.lineno)
    return lines
