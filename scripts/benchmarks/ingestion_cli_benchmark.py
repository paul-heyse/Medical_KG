#!/usr/bin/env python3
"""Placeholder benchmark harness for the unified ingestion CLI.

This script will be extended during rollout readiness (Task 16.6) to
exercise large NDJSON batches against staging adapters and capture
throughput metrics. For now it records the CLI startup overhead for a
`--dry-run` invocation to provide a baseline datapoint.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Sequence

from typer.testing import CliRunner

from Medical_KG.ingestion import cli


def run_once(argv: Sequence[str]) -> float:
    runner = CliRunner()
    started = time.perf_counter()
    result = runner.invoke(cli.app, list(argv))
    duration = time.perf_counter() - started
    if result.exit_code != 0:
        raise RuntimeError(f"Benchmark invocation failed: {result.stdout}\n{result.stderr}")
    return duration


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("adapter", help="Adapter to benchmark (must exist in registry)")
    parser.add_argument("--batch", type=Path, required=True, help="NDJSON payload for benchmarking")
    parser.add_argument("--iterations", type=int, default=3, help="Number of runs to average")
    parser.add_argument("--dry-run", action="store_true", help="Use --dry-run to avoid adapter execution")
    args = parser.parse_args(argv)

    argv_template = [args.adapter, "--batch", str(args.batch), "--summary-only"]
    if args.dry_run:
        argv_template.append("--dry-run")

    timings = [run_once(argv_template) for _ in range(max(args.iterations, 1))]
    average = sum(timings) / len(timings)
    print(f"Runs: {timings}")
    print(f"Average seconds: {average:.4f}")
    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
