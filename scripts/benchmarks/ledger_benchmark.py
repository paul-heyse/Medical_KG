"""Benchmark helper for measuring ledger enum-only performance."""

from __future__ import annotations

import argparse
import sys
import time
import types
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Iterable

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


def parse_args(argv: Iterable[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--documents", type=int, default=5000, help="Number of synthetic documents to load")
    parser.add_argument("--samples", type=int, default=5, help="Number of load iterations to average")
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
        del ledger  # ensure file handles closed
        timings = _measure_load_time(ledger_path, args.samples)
    mean = sum(timings) / len(timings)
    sorted_timings = sorted(timings)
    median = sorted_timings[len(sorted_timings) // 2]
    index = int(0.95 * (len(sorted_timings) - 1))
    p95 = sorted_timings[index]
    print(
        f"Generated {args.documents} documents / {transitions} transitions. "
        f"Load time: mean={mean:.4f}s median={median:.4f}s p95={p95:.4f}s"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
