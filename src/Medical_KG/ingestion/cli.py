from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Iterator, cast

import typer

if TYPE_CHECKING:  # pragma: no cover - typing support only
    from rich.progress import (  # type: ignore[import-not-found]
        BarColumn,
        Progress,
        TextColumn,
        TimeRemainingColumn,
    )
    RICH_AVAILABLE = True
else:  # pragma: no cover - optional progress dependency
    try:
        from rich.progress import (  # type: ignore[import-not-found]
            BarColumn,
            Progress,
            TextColumn,
            TimeRemainingColumn,
        )
    except ImportError:
        Progress = cast(Any, None)
        BarColumn = cast(Any, None)
        TextColumn = cast(Any, None)
        TimeRemainingColumn = cast(Any, None)
        RICH_AVAILABLE = False
    else:
        RICH_AVAILABLE = True

from Medical_KG.ingestion.cli_helpers import (
    EXIT_DATA_ERROR,
    EXIT_RUNTIME_ERROR,
    AdapterInvocationError,
    LedgerResumeError,
    format_cli_error,
    format_results,
    handle_ledger_resume,
    invoke_adapter_sync,
    load_ndjson_batch,
)
from Medical_KG.ingestion.ledger import IngestionLedger
from Medical_KG.ingestion.pipeline import AdapterRegistry, IngestionPipeline, PipelineResult

app = typer.Typer(help="Medical KG ingestion CLI")


def _resolve_registry() -> AdapterRegistry:  # pragma: no cover - simple import indirection
    from Medical_KG.ingestion import registry

    return registry


def _available_sources() -> list[str]:
    return _resolve_registry().available_sources()


def _load_batch(path: Path) -> Iterator[dict[str, Any]]:
    try:
        return load_ndjson_batch(path, error_factory=lambda msg: typer.BadParameter(msg))
    except OSError as exc:  # pragma: no cover - filesystem failure
        raise typer.BadParameter(f"Unable to read batch file {path}: {exc}") from exc


def _count_batch_records(path: Path) -> int:
    return sum(1 for _ in load_ndjson_batch(path, error_factory=lambda msg: typer.BadParameter(msg)))


def _chunk_parameters(
    params: Iterable[dict[str, Any]], chunk_size: int
) -> Iterator[list[dict[str, Any]]]:
    chunk: list[dict[str, Any]] = []
    for entry in params:
        chunk.append(dict(entry))
        if len(chunk) >= chunk_size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def _should_display_progress(quiet: bool) -> bool:
    return RICH_AVAILABLE and not quiet and sys.stderr.isatty()


def _create_progress() -> Progress | None:
    if not RICH_AVAILABLE:
        return None
    return Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("{task.completed}/{task.total or '?'} records"),
        TimeRemainingColumn(),
        transient=False,
    )


def _build_pipeline(ledger_path: Path) -> IngestionPipeline:
    ledger = IngestionLedger(ledger_path)
    return IngestionPipeline(ledger)


def _process_parameters(
    source: str,
    ledger: IngestionLedger,
    registry: AdapterRegistry,
    *,
    params: Iterable[dict[str, Any]] | None,
    resume: bool,
    auto: bool,
    chunk_size: int,
    quiet: bool,
    total: int | None,
) -> None:
    def _invoke(chunk: Iterable[dict[str, Any]] | None) -> list[PipelineResult]:
        try:
            return invoke_adapter_sync(
                source,
                ledger=ledger,
                registry=registry,
                params=chunk,
                resume=resume,
            )
        except AdapterInvocationError as exc:
            typer.echo(
                format_cli_error(
                    exc,
                    prefix="Ingestion failed",
                    remediation="Inspect the ledger for failing documents or retry with --resume.",
                ),
                err=True,
            )
            raise typer.Exit(code=EXIT_RUNTIME_ERROR) from exc

    def _emit(outputs: list[PipelineResult]) -> None:
        if not auto:
            return
        for line in format_results(outputs, output_format="jsonl"):
            typer.echo(line)

    if params is None:
        outputs = _invoke(None)
        _emit(outputs)
        return

    display_progress = _should_display_progress(quiet)
    chunks = _chunk_parameters(params, chunk_size)
    progress = _create_progress() if display_progress else None

    if progress is None:
        for chunk in chunks:
            outputs = _invoke(chunk)
            _emit(outputs)
        return

    with progress:
        task_id = progress.add_task("Processing batch", total=total)
        for chunk in chunks:
            outputs = _invoke(chunk)
            processed = sum(len(result.doc_ids) for result in outputs) or len(chunk)
            progress.advance(task_id, processed)
            _emit(outputs)


def ingest(
    source: str = typer.Argument(..., help="Source identifier", autocompletion=lambda: _available_sources()),
    batch: Path | None = typer.Option(None, help="Path to NDJSON with parameters"),
    auto: bool = typer.Option(False, help="Enable auto pipeline"),
    ledger_path: Path = typer.Option(Path(".ingest-ledger.jsonl"), help="Ledger storage"),
    ids: str | None = typer.Option(None, help="Comma separated document identifiers"),
    chunk_size: int = typer.Option(1000, min=1, help="Number of batch entries to process per chunk"),
    quiet: bool = typer.Option(False, help="Disable progress reporting"),
) -> None:
    """Run ingestion for the specified source."""

    known = _available_sources()
    if source not in known:
        raise typer.BadParameter(f"Unknown source '{source}'. Known sources: {', '.join(known)}")

    if ids and batch:
        raise typer.BadParameter("--ids cannot be combined with --batch")

    registry = _resolve_registry()
    ledger = IngestionLedger(ledger_path)
    params: Iterable[dict[str, Any]] | None = None
    total: int | None = None
    if ids:
        parsed = [identifier.strip() for identifier in ids.split(",") if identifier.strip()]
        params = [{"ids": parsed}]
    elif batch:
        total = _count_batch_records(batch)
        params = _load_batch(batch)

    _process_parameters(
        source,
        ledger,
        registry,
        params=params,
        resume=False,
        auto=auto,
        chunk_size=chunk_size,
        quiet=quiet,
        total=total,
    )


def resume(
    source: str = typer.Argument(..., help="Source identifier", autocompletion=lambda: _available_sources()),
    ledger_path: Path = typer.Option(Path(".ingest-ledger.jsonl"), help="Ledger storage"),
    auto: bool = typer.Option(False, help="Emit resumed doc IDs as JSON"),
    quiet: bool = typer.Option(False, help="Disable progress reporting"),
) -> None:
    """Retry ingestion while skipping documents already completed."""

    known = _available_sources()
    if source not in known:
        raise typer.BadParameter(f"Unknown source '{source}'. Known sources: {', '.join(known)}")

    ledger = IngestionLedger(ledger_path)
    registry = _resolve_registry()
    try:
        plan = handle_ledger_resume(ledger, dry_run=True)
    except LedgerResumeError as exc:
        typer.echo(
            format_cli_error(
                exc,
                prefix="Resume unavailable",
                remediation="Verify the ledger file is intact before retrying.",
            ),
            err=True,
        )
        raise typer.Exit(code=EXIT_DATA_ERROR) from exc

    if not quiet and plan.stats.total:
        typer.echo(
            f"Skipping {plan.stats.skipped} completed documents; resuming {plan.stats.remaining} pending."
        )

    _process_parameters(
        source,
        ledger,
        registry,
        params=None,
        resume=True,
        auto=auto,
        chunk_size=1,
        quiet=quiet,
        total=plan.stats.remaining or None,
    )


def status(
    ledger_path: Path = typer.Option(Path(".ingest-ledger.jsonl"), help="Ledger storage"),
    fmt: str = typer.Option("text", "--format", help="Output format: text or json"),
) -> None:
    """Display ledger status for ingestion runs."""

    pipeline = _build_pipeline(ledger_path)
    summary = pipeline.status()
    if fmt.lower() == "json":
        typer.echo(json.dumps(summary, default=str))
        return
    if not summary:
        typer.echo("No ledger entries recorded")
        return
    for state, entries in summary.items():
        typer.echo(f"{state}: {len(entries)}")


app.command("ingest")(ingest)
app.command("resume")(resume)
app.command("status")(status)


if __name__ == "__main__":  # pragma: no cover
    app()
