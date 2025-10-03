from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[2] / "ops" / "load_test" / "check_thresholds.py"
_spec = importlib.util.spec_from_file_location("load_test_thresholds", MODULE_PATH)
if _spec is None or _spec.loader is None:  # pragma: no cover - defensive
    raise RuntimeError("Unable to import check_thresholds module")
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)

load_metrics = _module.load_metrics
evaluate = _module.evaluate

HTML_SAMPLE = """<html><body>
<table>
<thead>
<tr><th>Type</th><th>Name</th><th>Requests</th><th>Failures</th><th>Median Response Time</th><th>95%</th><th>99%</th><th>Requests/s</th></tr>
</thead>
<tbody>
<tr><td>Aggregated</td><td>Aggregated</td><td>120</td><td>1</td><td>300</td><td>800</td><td>1200</td><td>48.5</td></tr>
<tr><td>POST</td><td>/retrieve [endpoint]</td><td>80</td><td>0</td><td>310</td><td>820</td><td>1300</td><td>32.0</td></tr>
<tr><td>POST</td><td>/extract/pico</td><td>40</td><td>1</td><td>750</td><td>1800</td><td>2300</td><td>16.0</td></tr>
</tbody>
</table>
</body></html>"""

CSV_SAMPLE = """Type,Name,Requests,Failures,Median Response Time,95%,99%,Requests/s\nAggregated,Aggregated,60,0,280,750,1000,24.0\n"""


@pytest.fixture()
def html_report(tmp_path: Path) -> Path:
    path = tmp_path / "report.html"
    path.write_text(HTML_SAMPLE)
    return path


@pytest.fixture()
def csv_report(tmp_path: Path) -> Path:
    path = tmp_path / "stats.csv"
    path.write_text(CSV_SAMPLE)
    return path


@pytest.fixture()
def budget_file(tmp_path: Path) -> Path:
    path = tmp_path / "budget.yaml"
    path.write_text(
        """
profiles:
  burst:
    aggregated:
      latency_ms:
        p95: 900
        p99: 1400
      error_rate: 0.05
      rps: 40
endpoints:
  /retrieve [endpoint]:
    latency_ms:
      p95: 900
  /extract/pico:
    latency_ms:
      p95: 1900
"""
    )
    return path


def test_load_metrics_from_html(html_report: Path) -> None:
    metrics = load_metrics(html_report)
    assert "Aggregated" in metrics
    aggregated = metrics["Aggregated"]
    assert aggregated.requests == 120
    assert aggregated.p95_ms == 800
    assert pytest.approx(aggregated.error_rate, 1e-3) == 1 / 120


def test_load_metrics_from_csv(csv_report: Path) -> None:
    metrics = load_metrics(csv_report)
    assert metrics["Aggregated"].p50_ms == 280
    assert metrics["Aggregated"].rps == 24.0


def test_evaluate_checks_thresholds(html_report: Path, budget_file: Path) -> None:
    metrics = load_metrics(html_report)
    budget = _module.load_budget(budget_file)
    checks = evaluate(metrics, budget, profile="burst")
    failed = [check for check in checks if not check.passed]
    assert not failed


def test_evaluate_flags_budget_failure(csv_report: Path, budget_file: Path) -> None:
    metrics = load_metrics(csv_report)
    budget = _module.load_budget(budget_file)
    checks = evaluate(metrics, budget, profile="burst")
    assert any(check.metric == "throughput_rps" and not check.passed for check in checks)
