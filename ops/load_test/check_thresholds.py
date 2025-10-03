#!/usr/bin/env python3
"""Validate Locust load-test reports against documented SLO budgets."""

from __future__ import annotations

import argparse
import csv
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Mapping, Sequence

from bs4 import BeautifulSoup

import yaml


# NOTE: These dataclasses are also imported by pytest test modules. When tests load this
# module via importlib, dataclasses complains if __module__ is None (Python 3.12+). To
# guard against that, ensure we register the module name explicitly before defining the
# dataclasses during dynamic imports.
if __name__ == "__main__":
    MODULE_NAME = __name__
else:
    MODULE_NAME = __name__ or "ops.load_test.check_thresholds"

sys.modules.setdefault(MODULE_NAME, sys.modules.get(__name__))


@dataclass(frozen=True)
class MetricSnapshot:
    """Load-test metrics for a single route/aggregate entry."""

    name: str
    requests: int
    failures: int
    median_ms: float | None
    p95_ms: float | None
    p99_ms: float | None
    rps: float | None

    @property
    def error_rate(self) -> float:
        if self.requests == 0:
            return 0.0
        return self.failures / self.requests

    @property
    def p50_ms(self) -> float | None:
        return self.median_ms


@dataclass(frozen=True)
class ThresholdCheck:
    target: str
    metric: str
    actual: float | None
    comparator: str
    threshold: float
    passed: bool
    detail: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate load-test output against budgets")
    parser.add_argument("report", type=Path, help="Path to Locust report (HTML or CSV)")
    parser.add_argument(
        "--budget",
        type=Path,
        default=Path("ops/load_test/budget.yaml"),
        help="YAML file containing latency, error-rate, and throughput budgets",
    )
    parser.add_argument(
        "--profile",
        default="burst",
        help="Budget profile to enforce (e.g. burst, steady)",
    )
    return parser.parse_args()


def load_budget(path: Path) -> Mapping[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Budget file not found: {path}")
    return yaml.safe_load(path.read_text())


def load_metrics(path: Path) -> Dict[str, MetricSnapshot]:
    if not path.exists():
        raise FileNotFoundError(f"Report not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".html":
        return _parse_html(path)
    if suffix == ".csv":
        return _parse_csv(path)
    raise ValueError(f"Unsupported report format for {path}")


def _parse_html(path: Path) -> Dict[str, MetricSnapshot]:
    soup = BeautifulSoup(path.read_text(), "html.parser")
    table = _locate_requests_table(soup)
    if table is None:
        raise ValueError("Unable to locate requests table in HTML report")

    headers = [normalize_header(th.get_text(strip=True)) for th in table.find("thead").find_all("th")]

    snapshots: Dict[str, MetricSnapshot] = {}
    for row in table.find("tbody").find_all("tr"):
        cells = [cell.get_text(strip=True) for cell in row.find_all(["td", "th"])]
        if len(cells) != len(headers):
            continue
        data = {headers[idx]: cells[idx] for idx in range(len(headers))}
        name = data.get("name") or data.get("route")
        if not name:
            continue
        snapshots[name] = _row_to_snapshot(data)
    return snapshots


def _locate_requests_table(soup: BeautifulSoup) -> Any:
    for candidate in soup.find_all("table"):
        header = candidate.find("thead")
        if not header:
            continue
        labels = [normalize_header(th.get_text(strip=True)) for th in header.find_all("th")]
        if {"name", "requests"}.issubset(labels) and ("95pct" in labels or "99pct" in labels):
            return candidate
    return None


def _parse_csv(path: Path) -> Dict[str, MetricSnapshot]:
    snapshots: Dict[str, MetricSnapshot] = {}
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            name = row.get("Name") or row.get("name")
            if not name:
                continue
            normalized = {normalize_header(key): value for key, value in row.items()}
            snapshots[name] = _row_to_snapshot(normalized)
    return snapshots


def _row_to_snapshot(data: Mapping[str, Any]) -> MetricSnapshot:
    def to_int(value: Any) -> int:
        try:
            return int(float(_clean_number(value)))
        except (TypeError, ValueError):
            return 0

    def to_float(value: Any) -> float | None:
        if value is None:
            return None
        text = _clean_number(value)
        if text is None:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    requests = to_int(data.get("requests"))
    failures = to_int(data.get("failures") or data.get("fails"))
    median_ms = to_float(data.get("median_response_time") or data.get("median") or data.get("50pct"))
    p95_ms = to_float(data.get("95pct") or data.get("95"))
    p99_ms = to_float(data.get("99pct") or data.get("99"))
    rps = to_float(data.get("requests_per_s") or data.get("requests_s") or data.get("rps"))

    name = str(data.get("name") or data.get("route") or data.get("type") or "")
    if not name:
        name = "Unnamed"

    return MetricSnapshot(
        name=name,
        requests=requests,
        failures=failures,
        median_ms=median_ms,
        p95_ms=p95_ms,
        p99_ms=p99_ms,
        rps=rps,
    )


def _clean_number(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text == "-":
        return None
    text = text.replace(",", "")
    for suffix in ("ms", "s", "req/s"):
        if text.endswith(suffix):
            text = text[: -len(suffix)]
            break
    if text.endswith("%"):
        try:
            return str(float(text[:-1]) / 100.0)
        except ValueError:
            return None
    return text


def normalize_header(label: str) -> str:
    text = label.strip().lower()
    replacements = {
        "%": "pct",
        "/": "_per_",
        " ": "_",
        "-": "_",
        "(ms)": "",
        "(s)": "",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    while "__" in text:
        text = text.replace("__", "_")
    return text.strip("_")


def evaluate(
    metrics: Mapping[str, MetricSnapshot],
    budget: Mapping[str, Any],
    profile: str,
) -> Sequence[ThresholdCheck]:
    defaults = budget.get("defaults", {})
    default_latency = defaults.get("latency_ms", {})
    default_error_rate = defaults.get("error_rate")
    default_rps = defaults.get("rps")

    checks: list[ThresholdCheck] = []

    def combined_latency(overrides: Mapping[str, Any] | None) -> Mapping[str, float]:
        merged = dict(default_latency)
        if overrides:
            merged.update({k: float(v) for k, v in overrides.items()})
        return merged

    def combined_error_rate(value: Any | None) -> float | None:
        return float(value) if value is not None else (float(default_error_rate) if default_error_rate is not None else None)

    def combined_rps(value: Any | None) -> float | None:
        return float(value) if value is not None else (float(default_rps) if default_rps is not None else None)

    def run_checks(target: str, snapshot: MetricSnapshot | None, spec: Mapping[str, Any]) -> None:
        latency_spec = combined_latency(spec.get("latency_ms"))
        error_spec = combined_error_rate(spec.get("error_rate"))
        rps_spec = combined_rps(spec.get("rps"))

        def add_check(metric: str, actual: float | None, comparator: str, threshold: float) -> None:
            passed = False
            if actual is not None:
                if comparator == "<=":
                    passed = actual <= threshold
                elif comparator == ">=":
                    passed = actual >= threshold
            checks.append(
                ThresholdCheck(
                    target=target,
                    metric=metric,
                    actual=actual,
                    comparator=comparator,
                    threshold=threshold,
                    passed=passed,
                    detail="metric missing" if actual is None else f"actual={actual:.2f}, threshold={threshold:.2f}",
                )
            )

        if latency_spec:
            for key, limit in latency_spec.items():
                actual = None
                if snapshot is not None:
                    if key == "p50":
                        actual = snapshot.p50_ms
                    elif key == "p95":
                        actual = snapshot.p95_ms
                    elif key == "p99":
                        actual = snapshot.p99_ms
                add_check(f"latency_{key}", actual, "<=", float(limit))

        if error_spec is not None:
            actual = snapshot.error_rate if snapshot is not None else None
            add_check("error_rate", actual, "<=", float(error_spec))

        if rps_spec is not None:
            actual = snapshot.rps if snapshot is not None else None
            add_check("throughput_rps", actual, ">=", float(rps_spec))

    profiles = budget.get("profiles", {})
    profile_spec = profiles.get(profile, {})
    aggregated_spec = profile_spec.get("aggregated", {})
    aggregate_snapshot = _find_aggregate(metrics)
    if aggregated_spec:
        run_checks("Aggregated", aggregate_snapshot, aggregated_spec)

    for name, spec in (budget.get("endpoints", {}) or {}).items():
        snapshot = metrics.get(name)
        run_checks(name, snapshot, spec)

    return checks


def _find_aggregate(metrics: Mapping[str, MetricSnapshot]) -> MetricSnapshot | None:
    for key in ("Aggregated", "Total", "ALL"):
        if key in metrics:
            return metrics[key]
    for snapshot in metrics.values():
        if snapshot.name.lower() in {"aggregated", "total"}:
            return snapshot
    return None


def main() -> int:
    args = parse_args()
    try:
        metrics = load_metrics(args.report)
        budget = load_budget(args.budget)
    except (FileNotFoundError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    checks = evaluate(metrics, budget, args.profile)
    failures = [check for check in checks if not check.passed]

    if not checks:
        print("warning: no checks executed (verify budget/profile configuration)")
        return 1

    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        actual_repr = "n/a" if check.actual is None else f"{check.actual:.2f}"
        print(f"[{status}] {check.target} :: {check.metric} ({actual_repr} {check.comparator} {check.threshold:.2f})")
        if not check.passed and check.actual is None:
            print("    detail: metric missing in report")

    if failures:
        print(f"\n{len(failures)} check(s) failed")
        return 1

    print("\nAll checks passed ✅")
    return 0


if __name__ == "__main__":
    sys.exit(main())
