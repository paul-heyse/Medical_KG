"""Benchmark helpers for the ingestion ledger state machine."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import types
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable

SRC_ROOT = Path(__file__).resolve().parents[2] / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

# Provide a lightweight package stub so importing ``Medical_KG`` does not pull in
# optional dependencies (fastapi, jsonschema, yaml, etc.) when running the
# benchmark on a bare environment. The stub exposes the package path so that the
# ledger module can be imported directly.
if "Medical_KG" not in sys.modules:
    pkg = types.ModuleType("Medical_KG")
    pkg.__path__ = [str(SRC_ROOT / "Medical_KG")]
    sys.modules["Medical_KG"] = pkg

if "Medical_KG.ingestion" not in sys.modules:
    subpkg = types.ModuleType("Medical_KG.ingestion")
    subpkg.__path__ = [str(SRC_ROOT / "Medical_KG" / "ingestion")]
    sys.modules["Medical_KG.ingestion"] = subpkg

if "httpx" not in sys.modules:  # pragma: no cover - optional dependency shim
    try:
        import httpx  # type: ignore  # noqa: F401
    except ImportError:  # pragma: no cover - lightweight stub for benchmarks
        httpx_module = types.ModuleType("httpx")

        class _AsyncClient:
            def __init__(self, *args: object, **kwargs: object) -> None:
                self.args = args
                self.kwargs = kwargs

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

from Medical_KG.ingestion.ledger import IngestionLedger, LedgerState

_DEFAULT_SEQUENCE: tuple[LedgerState, ...] = (
    LedgerState.PENDING,
    LedgerState.FETCHING,
    LedgerState.FETCHED,
    LedgerState.PARSING,
    LedgerState.PARSED,
    LedgerState.VALIDATING,
    LedgerState.VALIDATED,
    LedgerState.IR_BUILDING,
    LedgerState.IR_READY,
    LedgerState.COMPLETED,
)


def _generate_documents(ledger: IngestionLedger, documents: int) -> int:
    transitions = 0
    for index in range(documents):
        doc_id = f"doc-{index}"
        for state in _DEFAULT_SEQUENCE:
            ledger.update_state(doc_id, state)
            transitions += 1
    return transitions


def _measure_load_time(path: Path, samples: int) -> list[float]:
    results: list[float] = []
    for _ in range(samples):
        start = time.perf_counter()
        ledger = IngestionLedger(path)
        ledger.entries()  # materialise document cache
        end = time.perf_counter()
        results.append(end - start)
    return results


def _summarise_timings(label: str, timings: list[float]) -> dict[str, float]:
    mean = statistics.fmean(timings)
    median = statistics.median(timings)
    p95_index = int(round(0.95 * (len(sorted_timings := sorted(timings)) - 1)))
    p95 = sorted_timings[p95_index]
    summary = {"mean": mean, "median": median, "p95": p95}
    print(
        f"{label}: mean={mean:.4f}s median={median:.4f}s p95={p95:.4f}s"
    )
    return summary


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents", type=int, default=5000, help="Number of synthetic documents to load")
    parser.add_argument("--samples", type=int, default=5, help="Number of load iterations to average")
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Measure snapshot-assisted load times in addition to full log loads",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="Optional path to write benchmark summary as JSON",
    )
    parser.add_argument(
        "--keep-metrics",
        action="store_true",
        help="Do not disable Prometheus metric refresh during generation",
    )
    return parser.parse_args(argv)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)
    with TemporaryDirectory() as tmp:
        ledger_path = Path(tmp) / "ledger.jsonl"
        ledger = IngestionLedger(ledger_path)
        if not args.keep_metrics:
            ledger._refresh_state_metrics = lambda: None  # type: ignore[assignment]
        transitions = _generate_documents(ledger, args.documents)
        snapshot_path: Path | None = None
        if args.snapshot:
            snapshot_path = ledger.create_snapshot()
        del ledger  # ensure file handles closed
        summaries: dict[str, dict[str, float]] = {}
        full_loads = _measure_load_time(ledger_path, args.samples)
        summaries["full_log"] = _summarise_timings("Full log load", full_loads)
        if args.snapshot and snapshot_path is not None:
            snapshot_loads = _measure_load_time(ledger_path, args.samples)
            summaries["snapshot"] = _summarise_timings("Snapshot load", snapshot_loads)
            if full_loads and snapshot_loads:
                ratio = statistics.fmean(snapshot_loads) / statistics.fmean(full_loads)
                print(f"Snapshot speedup: {1/ratio:.2f}x faster")
        else:
            print("Snapshot timing skipped (invoke with --snapshot to measure)")
        if args.report:
            args.report.write_text(
                json.dumps(
                    {
                        "documents": args.documents,
                        "transitions": transitions,
                        "samples": args.samples,
                        "summaries": summaries,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            print(f"Wrote benchmark report to {args.report}")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
