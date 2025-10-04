from __future__ import annotations

import importlib
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Iterator, Mapping, Sequence, cast

from Medical_KG.ingestion.pipeline import PipelineResult

if TYPE_CHECKING:  # pragma: no cover - typing aids
    from rich.console import Console as RichConsole
    from rich.progress import Progress as RichProgress
    from rich.table import Table as RichTable
else:  # pragma: no cover - fallback types when rich is missing
    RichConsole = Any
    RichProgress = Any
    RichTable = Any

try:  # pragma: no cover - optional rich dependency
    _console_mod = importlib.import_module("rich.console")
    Console = getattr(_console_mod, "Console")
    _progress_mod = importlib.import_module("rich.progress")
    BarColumn = getattr(_progress_mod, "BarColumn")
    Progress = getattr(_progress_mod, "Progress")
    TextColumn = getattr(_progress_mod, "TextColumn")
    TimeElapsedColumn = getattr(_progress_mod, "TimeElapsedColumn")
    TimeRemainingColumn = getattr(_progress_mod, "TimeRemainingColumn")
    Table = getattr(importlib.import_module("rich.table"), "Table")
except Exception:  # pragma: no cover - fallback when rich is missing
    Console = None
    Progress = None
    BarColumn = None
    TextColumn = None
    TimeElapsedColumn = None
    TimeRemainingColumn = None
    Table = None


class BatchValidationError(ValueError):
    """Raised when a batch file contains invalid content."""

    def __init__(self, message: str, *, hint: str | None = None) -> None:
        super().__init__(message)
        self.hint = hint


@dataclass(slots=True)
class CLIResultSummary:
    """Aggregated details about a CLI ingestion run."""

    adapter: str
    resume: bool
    auto: bool
    batch_file: Path | None
    total_parameters: int | None
    processed_documents: int
    started_at: datetime
    completed_at: datetime
    results: list[PipelineResult]
    warnings: list[str]
    errors: list[str]

    @property
    def duration_seconds(self) -> float:
        return max((self.completed_at - self.started_at).total_seconds(), 0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter,
            "resume": self.resume,
            "auto": self.auto,
            "batch_file": str(self.batch_file) if self.batch_file else None,
            "total_parameters": self.total_parameters,
            "processed_documents": self.processed_documents,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "results": [
                {"source": result.source, "doc_ids": list(result.doc_ids)}
                for result in self.results
            ],
            "warnings": list(self.warnings),
            "errors": list(self.errors),
        }


def load_ndjson_batch(path: Path, *, strict: bool = True) -> Iterator[dict[str, Any]]:
    """Yield JSON objects from an NDJSON file, optionally enforcing strict validation."""

    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:  # pragma: no cover - validated via tests
                raise BatchValidationError(
                    f"Invalid JSON on line {index} of {path}: {exc.msg}",
                    hint="Ensure each line is a complete JSON object.",
                ) from exc
            if not isinstance(payload, Mapping):
                raise BatchValidationError(
                    "Batch entries must be JSON objects",
                    hint=f"Entry on line {index} is {type(payload).__name__}",
                )
            record = dict(payload)
            if strict:
                _validate_mapping(record, path, index)
            yield record


def count_ndjson_records(path: Path) -> int:
    """Count non-empty lines in an NDJSON file."""

    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def chunk_parameters(
    params: Iterable[dict[str, Any]],
    chunk_size: int,
) -> Iterator[list[dict[str, Any]]]:
    """Split parameters into chunks to bound memory usage."""

    chunk: list[dict[str, Any]] = []
    for entry in params:
        chunk.append(dict(entry))
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def should_display_progress(force: bool | None, quiet: bool) -> bool:
    if quiet:
        return False
    if force is True:
        return Progress is not None
    if force is False:
        return False
    return Progress is not None and sys.stderr.isatty()


def create_progress(description: str, total: int | None) -> tuple[Any, int] | None:
    if Progress is None:
        return None
    columns = [
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total or '?'}"),
        TimeElapsedColumn(),
    ]
    if total:
        columns.append(TimeRemainingColumn())
    progress = Progress(*columns, transient=False)
    task_id = progress.add_task(description, total=total)
    return progress, task_id


def format_cli_error(message: str, *, hint: str | None = None) -> str:
    if hint:
        return f"Error: {message}\nHint: {hint}"
    return f"Error: {message}"


def summarise_results(
    *,
    adapter: str,
    resume: bool,
    auto: bool,
    batch_file: Path | None,
    total_parameters: int | None,
    results: Sequence[PipelineResult],
    started_at: datetime,
    completed_at: datetime,
    warnings: Sequence[str],
    errors: Sequence[str],
) -> CLIResultSummary:
    processed = sum(len(result.doc_ids) for result in results)
    return CLIResultSummary(
        adapter=adapter,
        resume=resume,
        auto=auto,
        batch_file=batch_file,
        total_parameters=total_parameters,
        processed_documents=processed,
        started_at=started_at,
        completed_at=completed_at,
        results=list(results),
        warnings=list(warnings),
        errors=list(errors),
    )


def render_text_summary(
    summary: CLIResultSummary,
    *,
    show_timings: bool,
    summary_only: bool,
) -> str:
    lines = [
        f"Adapter: {summary.adapter}",
        f"Processed documents: {summary.processed_documents}",
    ]
    if summary.total_parameters is not None:
        lines.append(f"Batch records: {summary.total_parameters}")
    if summary.resume:
        lines.append("Mode: resume")
    if summary.auto:
        lines.append("Mode: auto")
    if summary.batch_file:
        lines.append(f"Batch file: {summary.batch_file}")
    if show_timings:
        lines.append(f"Duration: {summary.duration_seconds:.2f}s")
    if summary.warnings:
        lines.extend([f"Warning: {warning}" for warning in summary.warnings])
    if summary.errors:
        lines.extend([f"Error: {error}" for error in summary.errors])
    if not summary_only:
        for result in summary.results:
            lines.append(f"{result.source}: {', '.join(result.doc_ids) or '0 documents'}")
    return "\n".join(lines)


def render_table_summary(
    summary: CLIResultSummary,
    *,
    show_timings: bool,
    console: Any | None,
) -> str:
    if Table is None or console is None:
        return render_text_summary(summary, show_timings=show_timings, summary_only=False)
    table = Table(title="Ingestion Summary")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Adapter", summary.adapter)
    table.add_row("Processed", str(summary.processed_documents))
    table.add_row("Resume", "yes" if summary.resume else "no")
    table.add_row("Auto", "yes" if summary.auto else "no")
    if summary.batch_file:
        table.add_row("Batch file", str(summary.batch_file))
    if summary.total_parameters is not None:
        table.add_row("Batch records", str(summary.total_parameters))
    if show_timings:
        table.add_row("Duration", f"{summary.duration_seconds:.2f}s")
    console.begin_capture()
    console.print(table)
    return cast(str, console.end_capture())


def render_json_summary(summary: CLIResultSummary) -> str:
    return json.dumps(summary.to_dict(), indent=2)


def throttle(rate_limit_per_second: float | None, *, last_run: float | None) -> float:
    if not rate_limit_per_second or rate_limit_per_second <= 0:
        return time.monotonic()
    interval = 1.0 / rate_limit_per_second
    now = time.monotonic()
    if last_run is None:
        return now
    elapsed = now - last_run
    if elapsed < interval:
        time.sleep(interval - elapsed)
        return time.monotonic()
    return now


def _validate_mapping(record: Mapping[str, Any], path: Path, index: int) -> None:
    for key in record.keys():
        if not isinstance(key, str):
            raise BatchValidationError(
                "Batch entries must use string keys",
                hint=f"Entry on line {index} of {path} contains non-string keys",
            )


__all__ = [
    "BatchValidationError",
    "CLIResultSummary",
    "chunk_parameters",
    "count_ndjson_records",
    "create_progress",
    "format_cli_error",
    "load_ndjson_batch",
    "render_json_summary",
    "render_table_summary",
    "render_text_summary",
    "should_display_progress",
    "summarise_results",
    "throttle",
]
