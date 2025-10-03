from __future__ import annotations

import asyncio
import json
from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import ModuleType
from typing import Iterable, Mapping

import typer

from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.ledger import IngestionLedger

app = typer.Typer(help="Medical KG ingestion CLI")


def _resolve_registry() -> ModuleType:  # pragma: no cover - simple import indirection
    from Medical_KG.ingestion import registry

    return registry


def _available_sources() -> list[str]:
    return _resolve_registry().available_sources()


def _get_adapter(source: str, context: AdapterContext, client: AsyncHttpClient) -> BaseAdapter:
    return _resolve_registry().get_adapter(source, context, client)


def _load_batch(path: Path) -> Iterable[Mapping[str, object]]:
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        yield json.loads(line)


@app.command("ingest")
def ingest(
    source: str = typer.Argument(..., help="Source identifier", autocompletion=lambda: _available_sources()),
    batch: Path | None = typer.Option(None, help="Path to NDJSON with parameters"),
    auto: bool = typer.Option(False, help="Enable auto pipeline"),
    ledger_path: Path = typer.Option(Path(".ingest-ledger.jsonl"), help="Ledger storage"),
) -> None:
    """Run ingestion for the specified source."""

    known = _available_sources()
    if source not in known:
        raise typer.BadParameter(f"Unknown source '{source}'. Known sources: {', '.join(known)}")

    ledger = IngestionLedger(ledger_path)
    context = AdapterContext(ledger=ledger)
    client = AsyncHttpClient()
    adapter = _get_adapter(source, context, client)

    async def _run() -> None:
        try:
            if batch:
                for params in _load_batch(batch):
                    results = await adapter.run(**params)
                    if auto:
                        typer.echo(json.dumps([res.document.doc_id for res in results]))
            else:
                results = await adapter.run()
                if auto:
                    typer.echo(json.dumps([res.document.doc_id for res in results]))
        finally:
            await client.aclose()

    asyncio.run(_run())


if __name__ == "__main__":  # pragma: no cover
    app()
