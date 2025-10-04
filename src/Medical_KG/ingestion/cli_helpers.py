"""Shared ingestion CLI helpers.

This module centralises the ingestion command-line primitives so both the
legacy ``med ingest`` entry point and the Typer-based ingestion CLI can share
consistent behaviour.  Each helper is intentionally synchronous-friendly and
provides rich typing so callers can compose bespoke orchestration logic
without re-implementing JSON parsing, adapter lifecycle management, or
result formatting.

Example
-------

```python
from pathlib import Path

from Medical_KG.ingestion.cli_helpers import (
    DEFAULT_LEDGER_PATH,
    format_results,
    invoke_adapter_sync,
    load_ndjson_batch,
)

batch = Path("params.ndjson")
records = load_ndjson_batch(batch)
results = invoke_adapter_sync("pubmed", ledger=DEFAULT_LEDGER_PATH, params=records)
for line in format_results(results, output_format="jsonl"):
    print(line)
```
"""

from __future__ import annotations

import asyncio
import json
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import (
    Any,
    Callable,
    Collection,
    Iterable,
    Iterator,
    Mapping,
    Sequence,
    TextIO,
    cast,
    overload,
)

from Medical_KG.ingestion import registry as ingestion_registry
from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.ledger import IngestionLedger
from Medical_KG.ingestion.pipeline import AdapterRegistry, PipelineResult

BatchRecord = dict[str, Any]
BatchSource = Path | TextIO
ProgressCallback = Callable[[int, int | None], None]
ErrorFactory = Callable[[str], Exception]

EXIT_SUCCESS = 0
EXIT_DATA_ERROR = 64
EXIT_RUNTIME_ERROR = 70
DEFAULT_LEDGER_PATH = Path(".ingest-ledger.jsonl")
SUPPORTED_RESULT_FORMATS = frozenset({"text", "json", "table", "jsonl"})

_CompletedStates = frozenset({"auto_done", "manual_done"})


class BatchLoadError(ValueError):
    """Raised when NDJSON parsing fails."""


class AdapterInvocationError(RuntimeError):
    """Raised when adapter execution fails."""


class LedgerResumeError(RuntimeError):
    """Raised when ledger state prevents computing a resume plan."""


@dataclass(slots=True)
class LedgerResumeStats:
    """Aggregate details returned from :func:`handle_ledger_resume`."""

    total: int
    skipped: int
    remaining: int


@dataclass(slots=True)
class LedgerResumePlan:
    """Filtered resume payload produced by :func:`handle_ledger_resume`."""

    resume_ids: list[str]
    skipped_ids: list[str]
    stats: LedgerResumeStats
    dry_run: bool


def _make_error(message: str, error_factory: ErrorFactory | None) -> Exception:
    return error_factory(message) if error_factory else BatchLoadError(message)


def load_ndjson_batch(
    source: BatchSource,
    *,
    error_factory: ErrorFactory | None = None,
    progress: ProgressCallback | None = None,
    total: int | None = None,
) -> Iterator[BatchRecord]:
    """Yield JSON objects from an NDJSON stream.

    Parameters
    ----------
    source:
        Path to an NDJSON file or an open text handle.
    error_factory:
        Optional callable that converts validation messages into CLI-specific
        exceptions (e.g. :class:`typer.BadParameter`).
    progress:
        Optional callback invoked with ``(records_read, total_records)`` every
        time a record is emitted.  Useful for driving progress renderers.
    total:
        Total number of records expected; forwarded to the ``progress``
        callback when provided.
    """

    handle: TextIO
    if isinstance(source, Path):
        handle = cast(TextIO, source.open("r", encoding="utf-8"))
        close_handle = True
        origin = str(source)
    else:
        handle = source
        close_handle = False
        origin = getattr(source, "name", "<stream>")

    records_emitted = 0
    try:
        for index, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                message = f"Invalid JSON on line {index} of {origin}: {exc.msg}"
                raise _make_error(message, error_factory) from exc
            if not isinstance(payload, dict):
                message = (
                    "Batch entries must be JSON objects; "
                    f"found {type(payload).__name__} on line {index} of {origin}"
                )
                raise _make_error(message, error_factory)
            records_emitted += 1
            if progress:
                progress(records_emitted, total)
            yield dict(payload)
    finally:
        if close_handle:
            handle.close()


AdapterParams = Iterable[Mapping[str, Any]] | None


def _resolve_registry(registry: AdapterRegistry | None) -> AdapterRegistry:
    return registry or cast(AdapterRegistry, ingestion_registry)


async def invoke_adapter(
    source: str,
    *,
    ledger: IngestionLedger | Path,
    registry: AdapterRegistry | None = None,
    client_factory: Callable[[], AsyncHttpClient] | type[AsyncHttpClient] = AsyncHttpClient,
    params: AdapterParams = None,
    resume: bool = False,
) -> list[PipelineResult]:
    """Execute an adapter and return summarised pipeline results."""

    ledger_obj = ledger if isinstance(ledger, IngestionLedger) else IngestionLedger(Path(ledger))
    registry_obj = _resolve_registry(registry)

    try:
        client = client_factory()
    except Exception as exc:  # pragma: no cover - dependency guards
        raise AdapterInvocationError(f"Failed to construct HTTP client: {exc}") from exc

    outputs: list[PipelineResult] = []
    async with client:
        try:
            adapter = registry_obj.get_adapter(source, AdapterContext(ledger=ledger_obj), client)
        except Exception as exc:  # pragma: no cover - adapter resolution failures
            raise AdapterInvocationError(f"Unable to resolve adapter '{source}': {exc}") from exc

        try:
            if params is None:
                doc_ids = [
                    result.document.doc_id
                    async for result in adapter.iter_results(resume=resume)
                ]
                outputs.append(PipelineResult(source=source, doc_ids=doc_ids))
            else:
                for entry in params:
                    invocation_params = dict(entry)
                    doc_ids = [
                        result.document.doc_id
                        async for result in adapter.iter_results(
                            **invocation_params, resume=resume
                        )
                    ]
                    outputs.append(PipelineResult(source=source, doc_ids=doc_ids))
        except Exception as exc:
            raise AdapterInvocationError(f"Adapter '{source}' failed: {exc}") from exc
    return outputs


def invoke_adapter_sync(
    source: str,
    *,
    ledger: IngestionLedger | Path,
    registry: AdapterRegistry | None = None,
    client_factory: Callable[[], AsyncHttpClient] | type[AsyncHttpClient] = AsyncHttpClient,
    params: AdapterParams = None,
    resume: bool = False,
) -> list[PipelineResult]:
    """Synchronously execute :func:`invoke_adapter`."""

    return asyncio.run(
        invoke_adapter(
            source,
            ledger=ledger,
            registry=registry,
            client_factory=client_factory,
            params=params,
            resume=resume,
        )
    )


def format_cli_error(
    error: BaseException,
    *,
    prefix: str = "Error",
    remediation: str | None = None,
    include_stack: bool = False,
    use_color: bool | None = None,
) -> str:
    """Render a CLI-friendly error message."""

    message = str(error).strip() or error.__class__.__name__
    header = f"{prefix}: {message}" if prefix else message
    lines = [header]
    if remediation:
        lines.append(f"Hint: {remediation}")
    if include_stack:
        lines.append(traceback.format_exc().rstrip())

    if use_color is None:
        use_color = sys.stderr.isatty()
    if use_color:
        red = "\x1b[31m"
        cyan = "\x1b[36m"
        reset = "\x1b[0m"
        lines[0] = f"{red}{lines[0]}{reset}"
        if remediation:
            lines[1] = f"{cyan}{lines[1]}{reset}"
    return "\n".join(lines)


@overload
def handle_ledger_resume(
    ledger: IngestionLedger | Path,
    *,
    candidate_doc_ids: Iterable[str],
    dry_run: bool = False,
    completed_states: Collection[str] | None = None,
) -> LedgerResumePlan:
    ...


@overload
def handle_ledger_resume(
    ledger: IngestionLedger | Path,
    *,
    candidate_doc_ids: None = None,
    dry_run: bool = False,
    completed_states: Collection[str] | None = None,
) -> LedgerResumePlan:
    ...


def handle_ledger_resume(
    ledger: IngestionLedger | Path,
    *,
    candidate_doc_ids: Iterable[str] | None = None,
    dry_run: bool = False,
    completed_states: Collection[str] | None = None,
) -> LedgerResumePlan:
    """Compute resume metadata for a ledger."""

    completed_set = frozenset(completed_states or _CompletedStates)

    try:
        ledger_obj = ledger if isinstance(ledger, IngestionLedger) else IngestionLedger(Path(ledger))
    except Exception as exc:  # pragma: no cover - corrupted ledger
        raise LedgerResumeError(f"Unable to load ledger: {exc}") from exc

    entries = list(ledger_obj.entries())
    completed_ids = {entry.doc_id for entry in entries if entry.state in completed_set}
    pending_ids = {entry.doc_id for entry in entries if entry.state not in completed_set}

    resume_ids: list[str]
    skipped_ids: list[str]
    if candidate_doc_ids is None:
        resume_ids = sorted(pending_ids)
        skipped_ids = sorted(completed_ids)
        total = len(entries)
    else:
        resume_ids = []
        skipped_ids = []
        total = 0
        for doc_id in candidate_doc_ids:
            total += 1
            if doc_id in completed_ids:
                skipped_ids.append(doc_id)
            else:
                resume_ids.append(doc_id)

    stats = LedgerResumeStats(total=total, skipped=len(skipped_ids), remaining=len(resume_ids))
    return LedgerResumePlan(resume_ids=resume_ids, skipped_ids=skipped_ids, stats=stats, dry_run=dry_run)


def _format_table(results: Sequence[PipelineResult]) -> list[str]:
    headers = ("Source", "Documents")
    rows = [(result.source, ", ".join(result.doc_ids) or "-") for result in results]
    widths = [len(header) for header in headers]
    for source, docs in rows:
        widths[0] = max(widths[0], len(source))
        widths[1] = max(widths[1], len(docs))

    separator = f"+-{'-' * widths[0]}-+-{'-' * widths[1]}-+"
    header_row = f"| {headers[0].ljust(widths[0])} | {headers[1].ljust(widths[1])} |"
    lines = [separator, header_row, separator]
    for source, docs in rows:
        lines.append(f"| {source.ljust(widths[0])} | {docs.ljust(widths[1])} |")
    lines.append(separator)
    return lines


def format_results(
    results: Iterable[PipelineResult],
    *,
    output_format: str = "text",
    verbose: bool = False,
    timings: Mapping[str, float] | None = None,
) -> list[str]:
    """Format ingestion results for CLI display."""

    collected = list(results)
    fmt = output_format.lower()
    if fmt not in SUPPORTED_RESULT_FORMATS:
        raise ValueError(f"Unsupported output format '{output_format}'")

    total_batches = len(collected)
    total_documents = sum(len(result.doc_ids) for result in collected)

    if fmt == "jsonl":
        return [json.dumps(result.doc_ids) for result in collected]

    payload = {
        "batches": total_batches,
        "documents": total_documents,
        "results": [
            {"source": result.source, "doc_ids": list(result.doc_ids)} for result in collected
        ],
    }
    if timings:
        payload["timings"] = {key: float(value) for key, value in timings.items()}

    if fmt == "json":
        return [json.dumps(payload, sort_keys=True)]

    if fmt == "table":
        return _format_table(collected)

    lines = [
        f"Batches processed: {total_batches}",
        f"Documents ingested: {total_documents}",
    ]
    if timings:
        for key, value in timings.items():
            lines.append(f"{key}: {value:.2f}s")
    if verbose:
        for result in collected:
            doc_list = ", ".join(result.doc_ids) or "(none)"
            lines.append(f"- {result.source}: {doc_list}")
    return lines


__all__ = [
    "AdapterInvocationError",
    "BatchLoadError",
    "DEFAULT_LEDGER_PATH",
    "EXIT_DATA_ERROR",
    "EXIT_RUNTIME_ERROR",
    "EXIT_SUCCESS",
    "LedgerResumeError",
    "LedgerResumePlan",
    "LedgerResumeStats",
    "SUPPORTED_RESULT_FORMATS",
    "format_cli_error",
    "format_results",
    "handle_ledger_resume",
    "invoke_adapter",
    "invoke_adapter_sync",
    "load_ndjson_batch",
]
