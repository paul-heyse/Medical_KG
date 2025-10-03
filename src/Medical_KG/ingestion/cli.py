from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any, Iterable, Iterator, cast

import typer

if TYPE_CHECKING:  # pragma: no cover - typing support only
    from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn
    RICH_AVAILABLE = True
else:  # pragma: no cover - optional progress dependency
    try:
        from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn
    except ImportError:
        Progress = cast(Any, None)
        BarColumn = cast(Any, None)
        TextColumn = cast(Any, None)
        TimeRemainingColumn = cast(Any, None)
        RICH_AVAILABLE = False
    else:
        RICH_AVAILABLE = True

from Medical_KG.ingestion.ledger import IngestionLedger
from Medical_KG.ingestion.pipeline import AdapterRegistry, IngestionPipeline, PipelineResult

app = typer.Typer(help="Medical KG ingestion CLI")


def _resolve_registry() -> AdapterRegistry:  # pragma: no cover - simple import indirection
    from Medical_KG.ingestion import registry

    return registry


def _available_sources() -> list[str]:
    return _resolve_registry().available_sources()


def _load_batch(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for index, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:  # pragma: no cover - CLI validation
                raise typer.BadParameter(
                    f"Invalid JSON on line {index} of {path}: {exc.msg}"
                ) from exc
            if not isinstance(payload, dict):
                raise typer.BadParameter(
                    "Batch entries must be JSON objects; "
                    f"found {type(payload).__name__} on line {index}"
                )
            yield payload


def _count_batch_records(path: Path) -> int:
    with path.open("r", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


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


def _emit_results(results: Iterable[PipelineResult]) -> None:
    for result in results:
        typer.echo(json.dumps(result.doc_ids))


def _process_parameters(
    pipeline: IngestionPipeline,
    source: str,
    *,
    params: Iterable[dict[str, Any]] | None,
    resume: bool,
    auto: bool,
    chunk_size: int,
    quiet: bool,
    total: int | None,
) -> None:
    if params is None:
        results = pipeline.run(source, params=None, resume=resume)
        if auto:
            _emit_results(results)
        return

    display_progress = _should_display_progress(quiet)
    chunks = _chunk_parameters(params, chunk_size)
    progress = _create_progress() if display_progress else None
    if progress is None:
        for chunk in chunks:
            outputs = pipeline.run(source, params=chunk, resume=resume)
            if auto:
                _emit_results(outputs)
        return

    with progress:
        task_id = progress.add_task("Processing batch", total=total)
        for chunk in chunks:
            outputs = pipeline.run(source, params=chunk, resume=resume)
            processed = sum(len(result.doc_ids) for result in outputs) or len(chunk)
            progress.advance(task_id, processed)
            if auto:
                _emit_results(outputs)


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

    pipeline = _build_pipeline(ledger_path)
    params: Iterable[dict[str, Any]] | None = None
    total: int | None = None
    if ids:
        parsed = [identifier.strip() for identifier in ids.split(",") if identifier.strip()]
        params = [{"ids": parsed}]
    elif batch:
        total = _count_batch_records(batch)
        params = _load_batch(batch)

    _process_parameters(
        pipeline,
        source,
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

    pipeline = _build_pipeline(ledger_path)
    _process_parameters(
        pipeline,
        source,
        params=None,
        resume=True,
        auto=auto,
        chunk_size=1,
        quiet=quiet,
        total=None,
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
