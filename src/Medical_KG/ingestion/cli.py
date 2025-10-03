from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Iterator

import typer

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


def _build_pipeline(ledger_path: Path) -> IngestionPipeline:
    ledger = IngestionLedger(ledger_path)
    return IngestionPipeline(ledger)


def _emit_results(results: Iterable[PipelineResult]) -> None:
    for result in results:
        typer.echo(json.dumps(result.doc_ids))


def ingest(
    source: str = typer.Argument(..., help="Source identifier", autocompletion=lambda: _available_sources()),
    batch: Path | None = typer.Option(None, help="Path to NDJSON with parameters"),
    auto: bool = typer.Option(False, help="Enable auto pipeline"),
    ledger_path: Path = typer.Option(Path(".ingest-ledger.jsonl"), help="Ledger storage"),
    ids: str | None = typer.Option(None, help="Comma separated document identifiers"),
) -> None:
    """Run ingestion for the specified source."""

    known = _available_sources()
    if source not in known:
        raise typer.BadParameter(f"Unknown source '{source}'. Known sources: {', '.join(known)}")

    if ids and batch:
        raise typer.BadParameter("--ids cannot be combined with --batch")

    pipeline = _build_pipeline(ledger_path)
    params: Iterable[dict[str, Any]] | None = None
    if ids:
        parsed = [identifier.strip() for identifier in ids.split(",") if identifier.strip()]
        params = [{"ids": parsed}]
    elif batch:
        params = list(_load_batch(batch))

    results = pipeline.run(source, params=params, resume=False)
    if auto:
        _emit_results(results)


def resume(
    source: str = typer.Argument(..., help="Source identifier", autocompletion=lambda: _available_sources()),
    ledger_path: Path = typer.Option(Path(".ingest-ledger.jsonl"), help="Ledger storage"),
    auto: bool = typer.Option(False, help="Emit resumed doc IDs as JSON"),
) -> None:
    """Retry ingestion while skipping documents already completed."""

    known = _available_sources()
    if source not in known:
        raise typer.BadParameter(f"Unknown source '{source}'. Known sources: {', '.join(known)}")

    pipeline = _build_pipeline(ledger_path)
    results = pipeline.run(source, params=None, resume=True)
    if auto:
        _emit_results(results)


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
