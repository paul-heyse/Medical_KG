from __future__ import annotations

import asyncio
import json
import hashlib
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

import typer

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.ledger import IngestionLedger

app = typer.Typer(help="Medical KG ingestion CLI")

_TASK_PENDING = "cli_pending"
_TASK_FAILED = "cli_failed"
_TASK_COMPLETED = "cli_completed"


def _resolve_registry():  # pragma: no cover - simple import indirection
    from Medical_KG.ingestion import registry

    return registry


def _available_sources() -> list[str]:
    return _resolve_registry().available_sources()


def _get_adapter(source: str, context: AdapterContext, client: AsyncHttpClient):
    return _resolve_registry().get_adapter(source, context, client)


def _load_batch(path: Path) -> Iterable[dict[str, Any]]:
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        yield json.loads(line)


def _parse_ids(ids: str | None) -> list[str]:
    if not ids:
        return []
    return [identifier.strip() for identifier in ids.split(",") if identifier.strip()]


def _task_id(source: str, params: Mapping[str, Any]) -> str:
    normalized = json.dumps(params, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
    return f"task:{source}:{digest}"


def _iter_pending_tasks(ledger: IngestionLedger, source: str) -> Iterator[tuple[str, Mapping[str, Any]]]:
    for entry in ledger.entries():
        if not entry.doc_id.startswith("task:"):
            continue
        if entry.metadata.get("source") != source:
            continue
        if entry.state == _TASK_COMPLETED:
            continue
        params = entry.metadata.get("params")
        if isinstance(params, Mapping):
            yield entry.doc_id, params


async def _execute_tasks(
    adapter: Any,
    ledger: IngestionLedger,
    source: str,
    tasks: Iterable[Mapping[str, Any]],
    *,
    auto: bool,
) -> None:
    errors: list[str] = []
    for params in tasks:
        task_id = _task_id(source, params)
        existing = ledger.get(task_id)
        if existing and existing.state == _TASK_COMPLETED:
            continue
        ledger.record(task_id, state=_TASK_PENDING, metadata={"source": source, "params": dict(params)})
        try:
            results = await adapter.run(**params)
        except Exception as exc:  # pragma: no cover - surfaced in tests
            ledger.record(
                task_id,
                state=_TASK_FAILED,
                metadata={"source": source, "params": dict(params), "error": str(exc)},
            )
            errors.append(str(exc))
            continue
        ledger.record(task_id, state=_TASK_COMPLETED, metadata={"source": source, "params": dict(params)})
        if auto:
            typer.echo(json.dumps([res.document.doc_id for res in results]))
    if errors:
        raise typer.Exit(code=1)


@app.command("ingest")
def ingest(
    source: str = typer.Argument(..., help="Source identifier", autocompletion=lambda: _available_sources()),
    batch: Path | None = typer.Option(None, help="Path to NDJSON with parameters"),
    ids: str | None = typer.Option(None, help="Comma separated identifiers to ingest"),
    auto: bool = typer.Option(False, help="Enable auto pipeline"),
    ledger_path: Path = typer.Option(Path(".ingest-ledger.jsonl"), help="Ledger storage"),
) -> None:
    """Run ingestion for the specified source."""

    known = _available_sources()
    if source not in known:
        raise typer.BadParameter(f"Unknown source '{source}'. Known sources: {', '.join(known)}")

    if batch and ids:
        raise typer.BadParameter("Provide either --batch or --ids, not both")

    ledger = IngestionLedger(ledger_path)
    context = AdapterContext(ledger=ledger)
    client = AsyncHttpClient()
    adapter = _get_adapter(source, context, client)

    def _task_params() -> list[Mapping[str, Any]]:
        if batch:
            return list(_load_batch(batch))
        if ids:
            return [{"id": identifier} for identifier in _parse_ids(ids)]
        return [{}]

    tasks = _task_params()

    async def _run() -> None:
        try:
            await _execute_tasks(adapter, ledger, source, tasks, auto=auto)
        finally:
            await client.aclose()

    asyncio.run(_run())


@app.command("resume")
def resume(
    source: str = typer.Argument(..., help="Source identifier", autocompletion=lambda: _available_sources()),
    ledger_path: Path = typer.Option(Path(".ingest-ledger.jsonl"), help="Ledger storage"),
    auto: bool = typer.Option(False, help="Echo document identifiers for resumed runs"),
) -> None:
    """Retry pending or failed ingestion tasks recorded in the ledger."""

    known = _available_sources()
    if source not in known:
        raise typer.BadParameter(f"Unknown source '{source}'. Known sources: {', '.join(known)}")

    ledger = IngestionLedger(ledger_path)
    context = AdapterContext(ledger=ledger)
    client = AsyncHttpClient()
    adapter = _get_adapter(source, context, client)
    tasks = [params for _task, params in _iter_pending_tasks(ledger, source)]

    async def _run() -> None:
        try:
            if not tasks:
                return
            await _execute_tasks(adapter, ledger, source, tasks, auto=auto)
        finally:
            await client.aclose()

    asyncio.run(_run())


@app.command("status")
def status(
    ledger_path: Path = typer.Argument(Path(".ingest-ledger.jsonl"), help="Ledger path"),
    format: str = typer.Option("text", "--format", help="Output format: text or json"),
) -> None:
    """Print summary of ingestion ledger states."""

    ledger = IngestionLedger(ledger_path)
    entries = list(ledger.entries())
    summary = Counter(entry.state for entry in entries)

    if format == "json":
        payload = {
            "total": len(entries),
            "states": dict(summary),
        }
        typer.echo(json.dumps(payload, sort_keys=True))
        return

    lines = [f"{state}: {count}" for state, count in sorted(summary.items())]
    typer.echo("\n".join(lines))


if __name__ == "__main__":  # pragma: no cover
    app()
