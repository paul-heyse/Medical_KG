"""Unified ingestion command-line interface.

Examples
--------
Run a batch ingestion job:

    med ingest pubmed --batch articles.ndjson --resume

Stream auto mode results with JSON output:

    med ingest clinicaltrials --auto --output json --limit 100
"""

from __future__ import annotations

import contextlib
import importlib
import itertools
import json
import logging
import sys
import textwrap
from datetime import datetime, timezone
from enum import Enum, IntEnum
from importlib import metadata
from pathlib import Path
from typing import Any, Callable, Iterator, Optional, Sequence, cast

import typer

from Medical_KG.ingestion.cli_helpers import (
    BatchValidationError,
    CLIResultSummary,
    chunk_parameters,
    count_ndjson_records,
    create_progress,
    format_cli_error,
    load_ndjson_batch,
    render_json_summary,
    render_table_summary,
    render_text_summary,
    should_display_progress,
    summarise_results,
    throttle,
)
from Medical_KG.ingestion.ledger import IngestionLedger
from Medical_KG.ingestion.pipeline import IngestionPipeline, PipelineResult

try:  # pragma: no cover - optional rich dependency
    Console = getattr(importlib.import_module("rich.console"), "Console")
except Exception:  # pragma: no cover - fallback when rich is absent
    Console = None

app = typer.Typer(
    help="Medical KG unified ingestion CLI",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)

_INGEST_HELP = textwrap.dedent(
    """
    Unified ingestion interface for all Medical KG adapters.

    The command accepts an adapter name followed by flags shared across batch, auto,
    and resume workflows. Short aliases mirror the most common operations so
    existing scripts migrate with minimal churn.

    **Examples**

    • `med ingest demo --batch params.ndjson --resume`
    • `med ingest umls --auto --limit 1000 --output json`
    • `med ingest nice --batch nice.ndjson --schema schemas/nice.json`
    """
)

_INGEST_EPILOG = textwrap.dedent(
    """
    See also: docs/ingestion_runbooks.md, docs/ingestion_cli_reference.md,
    docs/ingestion_cli_migration_guide.md
    """
)


class OutputFormat(str, Enum):
    TEXT = "text"
    JSON = "json"
    TABLE = "table"


class ExitCode(IntEnum):
    SUCCESS = 0
    FAILURE = 1
    INVALID_USAGE = 2


def _resolve_registry() -> Any:  # pragma: no cover - import indirection
    from Medical_KG.ingestion import registry

    return registry


def _available_sources() -> list[str]:
    try:
        return sorted(_resolve_registry().available_sources())
    except Exception:  # pragma: no cover - defensive import failure handling
        return []
def _complete_adapter(
    ctx: typer.Context,
    incomplete: str,
) -> list[str]:
    """Provide adapter name completions for Typer."""
    # Signature parameters are required so Typer's callback validation passes even
    # though we do not currently use them. Mark them as used to satisfy linters.
    _ = (ctx, incomplete)
    return _available_sources()


def _build_pipeline(ledger_path: Path) -> IngestionPipeline:
    ledger = IngestionLedger(ledger_path)
    return IngestionPipeline(ledger)


def _load_json_schema_validator(path: Path) -> Callable[[dict[str, Any]], None]:
    try:
        import jsonschema
    except Exception as exc:  # pragma: no cover - optional dependency handling
        raise typer.BadParameter(
            "jsonschema is required when using --schema. Install it via 'micromamba install jsonschema' or 'pip install jsonschema'."
        ) from exc

    try:
        with path.open("r", encoding="utf-8") as handle:
            schema = json.load(handle)
    except json.JSONDecodeError as exc:
        raise typer.BadParameter(f"Failed to parse JSON schema at {path}: {exc.msg}") from exc

    try:
        validator_cls = jsonschema.validators.validator_for(schema)
        validator_cls.check_schema(schema)
        validator = validator_cls(schema)
    except jsonschema.SchemaError as exc:
        raise typer.BadParameter(f"Schema at {path} is invalid: {exc.message}") from exc

    def _validate(instance: dict[str, Any]) -> None:
        try:
            validator.validate(instance)
        except jsonschema.ValidationError as exc:
            location = "/".join(str(part) for part in exc.path) or "<root>"
            raise BatchValidationError(
                f"Schema validation failed at {location}: {exc.message}",
                hint="Update the NDJSON payload or adjust the provided schema.",
            ) from exc

    return _validate


def _version_callback(value: bool) -> None:
    if not value:
        return
    try:
        package_version = metadata.version("Medical_KG")
    except metadata.PackageNotFoundError:  # pragma: no cover - local development
        package_version = "0.0.0"
    typer.echo(package_version)
    raise typer.Exit(code=ExitCode.SUCCESS.value)


def _configure_logging(log_level: str, log_file: Path | None, verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.getLevelName(log_level.upper())
    handlers: list[logging.Handler] = []
    formatter = logging.Formatter("%(levelname)s %(name)s: %(message)s")
    if log_file:
        handlers.append(logging.FileHandler(log_file, encoding="utf-8"))
    else:
        handlers.append(logging.StreamHandler(sys.stderr))
    for handler in handlers:
        handler.setFormatter(formatter)
    logging.basicConfig(level=level, handlers=handlers, force=True)


def _merge_options(base: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    if not base:
        return dict(payload)
    merged = dict(base)
    merged.update(payload)
    return merged


def _emit_doc_ids(results: Sequence[PipelineResult]) -> None:
    for result in results:
        if result.doc_ids:
            typer.echo(json.dumps(result.doc_ids))


def _emit_summary(
    summary: CLIResultSummary,
    *,
    output: OutputFormat,
    show_timings: bool,
    summary_only: bool,
) -> None:
    if output is OutputFormat.JSON:
        payload = render_json_summary(summary)
    elif output is OutputFormat.TABLE:
        console = Console(record=True) if Console else None
        payload = render_table_summary(summary, show_timings=show_timings, console=console)
    else:
        payload = render_text_summary(
            summary,
            show_timings=show_timings,
            summary_only=summary_only,
        )
    typer.echo(payload)


def _log_error(error_log: Path | None, *, payload: dict[str, Any]) -> None:
    if not error_log:
        return
    error_log.parent.mkdir(parents=True, exist_ok=True)
    with error_log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")


def _validate_dates(start_date: datetime | None, end_date: datetime | None) -> None:
    if start_date and end_date and start_date > end_date:
        raise typer.BadParameter("--start-date must be before --end-date")


def _dry_run(
    *,
    adapter: str,
    batch: Path | None,
    ids: list[str] | None,
    limit: int | None,
    strict_validation: bool,
    skip_validation: bool,
    resume: bool,
    auto: bool,
    show_timings: bool,
    summary_only: bool,
    output: OutputFormat,
    schema_validator: Callable[[dict[str, Any]], None] | None,
) -> None:
    warnings: list[str] = []
    if skip_validation:
        warnings.append("Validation skipped by user request (--skip-validation)")
    if schema_validator is not None and batch is not None:
        warnings.append("Batch entries validated against provided JSON schema")
    total_records: int | None = None
    if ids:
        total_records = len(ids) if limit is None else min(len(ids), limit)
    elif batch:
        total_records = count_ndjson_records(batch)
        if strict_validation and total_records == 0:
            raise typer.BadParameter("Batch file is empty")
        iterator = load_ndjson_batch(batch, strict=not skip_validation)
        iterator = cast(
            Iterator[dict[str, Any]],
            _apply_schema_validation(iterator, validator=schema_validator),
        )
        processed = 0
        for _ in iterator:
            processed += 1
            if limit is not None and processed >= limit:
                break
        total_records = processed
    elif limit is not None:
        total_records = limit
    else:
        total_records = None
    now = datetime.now(timezone.utc)
    summary = summarise_results(
        adapter=adapter,
        resume=resume,
        auto=auto,
        batch_file=batch,
        total_parameters=total_records,
        results=[],
        started_at=now,
        completed_at=now,
        warnings=warnings,
        errors=[],
    )
    _emit_summary(summary, output=output, show_timings=show_timings, summary_only=summary_only)


def _parameter_stream(
    *,
    batch: Path | None,
    ids: list[str] | None,
    skip_validation: bool,
) -> tuple[Iterator[dict[str, Any]] | None, int | None]:
    if ids:
        params = [{"ids": ids}]
        return iter(params), len(ids)
    if batch:
        total = count_ndjson_records(batch)
        iterator = load_ndjson_batch(batch, strict=not skip_validation)
        return iterator, total
    return None, None


def _apply_limit(
    iterator: Iterator[dict[str, Any]] | None,
    *,
    limit: int | None,
) -> Iterator[dict[str, Any]] | None:
    if iterator is None or limit is None:
        return iterator
    return iter(itertools.islice(iterator, limit))


def _apply_schema_validation(
    iterator: Iterator[dict[str, Any]] | None,
    *,
    validator: Callable[[dict[str, Any]], None] | None,
) -> Iterator[dict[str, Any]] | None:
    if iterator is None or validator is None:
        return iterator

    def _generator() -> Iterator[dict[str, Any]]:
        for entry in iterator:
            validator(entry)
            yield entry

    return _generator()


def _adapter_help() -> str:
    sources = _available_sources()
    if not sources:
        return "Adapter to execute (no adapters available)"
    listed = ", ".join(sources)
    return f"Adapter to execute. Available adapters: {listed}"


class _AdapterHelpText:
    """Lazy adapter help so tests can monkeypatch available sources."""

    def _value(self) -> str:
        return _adapter_help()

    def __str__(self) -> str:  # pragma: no cover - exercised via CLI help output
        return self._value()

    def __getattr__(self, name: str) -> Any:  # pragma: no cover - used by Click formatting
        return getattr(self._value(), name)


def ingest(
    adapter: str = typer.Argument(
        ...,
        help=cast(str, _AdapterHelpText()),
        autocompletion=_complete_adapter,
        metavar="ADAPTER",
    ),
    batch: Path | None = typer.Option(
        None,
        "--batch",
        "-b",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Path to NDJSON batch parameters",
    ),
    resume: bool = typer.Option(False, "--resume", "-r", help="Resume from ledger state"),
    auto: bool = typer.Option(False, "--auto", help="Emit document IDs as records complete"),
    output: OutputFormat = typer.Option(
        OutputFormat.TEXT,
        "--output",
        "-o",
        case_sensitive=False,
        help="Output format: text, json, or table",
    ),
    ledger_path: Path = typer.Option(
        Path(".ingest-ledger.jsonl"),
        "--ledger",
        help="Path to ingestion ledger JSONL",
    ),
    limit: int | None = typer.Option(None, "--limit", "-n", min=1, help="Maximum records to process"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate inputs without executing adapters"),
    chunk_size: int = typer.Option(
        1000,
        "--chunk-size",
        min=1,
        help="Number of batch entries to send per adapter invocation",
    ),
    ids: list[str] = typer.Option(
        [],
        "--id",
        help="Process a specific document identifier (repeatable)",
    ),
    start_date: datetime | None = typer.Option(
        None,
        "--start-date",
        help="Filter auto mode to documents updated after this ISO timestamp",
    ),
    end_date: datetime | None = typer.Option(
        None,
        "--end-date",
        help="Filter auto mode to documents updated before this ISO timestamp",
    ),
    page_size: int | None = typer.Option(None, "--page-size", min=1, help="Override adapter pagination size"),
    rate_limit: float | None = typer.Option(
        None,
        "--rate-limit",
        help="Maximum adapter invocations per second",
    ),
    progress: bool | None = typer.Option(
        None,
        "--progress/--no-progress",
        help="Force enable or disable the progress bar",
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
    quiet: bool = typer.Option(False, "--quiet", "-q", help="Reduce non-essential output"),
    log_file: Path | None = typer.Option(None, "--log-file", help="Write logs to the given file"),
    log_level: str = typer.Option("INFO", "--log-level", help="Logging level (DEBUG, INFO, WARNING, ERROR)"),
    strict_validation: bool = typer.Option(False, "--strict-validation", help="Enable strict batch validation"),
    skip_validation: bool = typer.Option(False, "--skip-validation", help="Skip optional validation checks"),
    fail_fast: bool = typer.Option(False, "--fail-fast", help="Abort on first adapter error"),
    error_log: Path | None = typer.Option(None, "--error-log", help="Write detailed errors to a JSONL file"),
    show_timings: bool = typer.Option(False, "--show-timings", help="Include duration in summary output"),
    summary_only: bool = typer.Option(False, "--summary-only", help="Suppress per-result output"),
    schema_path: Path | None = typer.Option(
        None,
        "--schema",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        help="Optional JSON Schema to validate batch parameters",
    ),
    version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show CLI version and exit",
    ),
) -> None:
    del version  # handled by callback
    adapter_name = adapter
    identifier_list = ids or None
    _validate_dates(start_date, end_date)
    known_sources = _available_sources()
    if adapter_name not in known_sources:
        raise typer.BadParameter(
            f"Unknown source '{adapter_name}'. Known sources: {', '.join(known_sources)}"
        )

    if identifier_list and batch:
        raise typer.BadParameter("--id cannot be combined with --batch")
    if strict_validation and skip_validation:
        raise typer.BadParameter("--strict-validation cannot be combined with --skip-validation")
    _configure_logging(log_level, log_file, verbose)
    schema_validator: Callable[[dict[str, Any]], None] | None = None
    if schema_path is not None:
        schema_validator = _load_json_schema_validator(schema_path)
    if dry_run:
        _dry_run(
            adapter=adapter_name,
            batch=batch,
            ids=identifier_list,
            limit=limit,
            strict_validation=strict_validation,
            skip_validation=skip_validation,
            resume=resume,
            auto=auto,
            show_timings=show_timings,
            summary_only=summary_only,
            output=output,
            schema_validator=schema_validator,
        )
        return
    raw_params_iter, total_records = _parameter_stream(
        batch=batch,
        ids=identifier_list,
        skip_validation=skip_validation,
    )
    params_iter_unlimited = _apply_schema_validation(
        raw_params_iter, validator=schema_validator
    )
    if batch and strict_validation and (total_records or 0) == 0:
        raise typer.BadParameter("Batch file is empty")
    if limit is not None and total_records is not None:
        total_records = min(total_records, limit)
    params_iter: Optional[Iterator[dict[str, Any]]] = _apply_limit(
        params_iter_unlimited, limit=limit
    )
    pipeline = _build_pipeline(ledger_path)
    base_options: dict[str, Any] = {}
    if start_date:
        base_options["start_date"] = start_date.isoformat()
    if end_date:
        base_options["end_date"] = end_date.isoformat()
    if page_size is not None:
        base_options["page_size"] = page_size
    if limit is not None and params_iter is None:
        base_options.setdefault("limit", limit)
    warnings: list[str] = []
    if skip_validation:
        warnings.append("Validation skipped by user request (--skip-validation)")
    if schema_validator is not None and batch is not None:
        warnings.append("Batch entries validated against provided JSON schema")
    display_progress = should_display_progress(progress, quiet)
    progress_bar: Any | None = None
    progress_task: int | None = None
    if display_progress:
        progress_pair = create_progress("Ingesting", total_records)
        if progress_pair is not None:
            progress_bar, progress_task = progress_pair
    errors: list[str] = []
    results: list[PipelineResult] = []
    started_at = datetime.now(timezone.utc)
    last_tick: float | None = None
    progress_context = progress_bar if progress_bar is not None else contextlib.nullcontext()
    try:
        with progress_context:
            if params_iter is None:
                invocation_params = [base_options] if base_options else None
                outputs = pipeline.run(adapter_name, params=invocation_params, resume=resume)
                results.extend(outputs)
                if auto and not summary_only:
                    _emit_doc_ids(outputs)
            else:
                processed = 0
                for chunk in chunk_parameters(params_iter, chunk_size):
                    chunk_with_options = [_merge_options(base_options, entry) for entry in chunk]
                    if not chunk_with_options:
                        continue
                    outputs = pipeline.run(adapter_name, params=chunk_with_options, resume=resume)
                    results.extend(outputs)
                    processed += len(chunk_with_options)
                    processed_docs = sum(len(item.doc_ids) for item in outputs) or len(chunk_with_options)
                    if progress_bar is not None and progress_task is not None:
                        progress_bar.advance(progress_task, processed_docs)
                    if auto and not summary_only:
                        _emit_doc_ids(outputs)
                    if fail_fast and any(len(item.doc_ids) == 0 for item in outputs):
                        raise RuntimeError("Adapter returned no documents for at least one invocation")
                    if limit is not None and processed >= limit:
                        break
                    last_tick = throttle(rate_limit, last_run=last_tick)
    except BatchValidationError as exc:
        message = format_cli_error(str(exc), hint=exc.hint)
        _log_error(error_log, payload={"adapter": adapter_name, "error": message})
        typer.echo(message, err=True)
        raise typer.Exit(code=ExitCode.INVALID_USAGE.value) from exc
    except typer.BadParameter:
        raise
    except Exception as exc:  # pragma: no cover - defensive error handling
        message = format_cli_error(str(exc))
        _log_error(
            error_log,
            payload={"adapter": adapter_name, "error": message, "exception": exc.__class__.__name__},
        )
        errors.append(str(exc))
    completed_at = datetime.now(timezone.utc)
    summary = summarise_results(
        adapter=adapter_name,
        resume=resume,
        auto=auto,
        batch_file=batch,
        total_parameters=total_records,
        results=results,
        started_at=started_at,
        completed_at=completed_at,
        warnings=warnings,
        errors=errors,
    )
    _emit_summary(summary, output=output, show_timings=show_timings, summary_only=summary_only)
    if errors:
        raise typer.Exit(code=ExitCode.FAILURE.value)


app.command(help=_INGEST_HELP, epilog=_INGEST_EPILOG)(ingest)


def main(argv: list[str] | None = None) -> int:
    command = typer.main.get_command(app)
    args = list(argv or [])
    prog_name = "med"
    if args and args[0] == "ingest":
        args = args[1:]
        prog_name = "med ingest"
    try:
        command.main(args=args, prog_name=prog_name, standalone_mode=False)
    except SystemExit as exc:  # pragma: no cover - delegated to entry point
        return int(exc.code or 0)
    return 0


if __name__ == "__main__":  # pragma: no cover - manual invocation
    raise SystemExit(main())
