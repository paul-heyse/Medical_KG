from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any, Iterable

import typer

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.ledger import IngestionLedger
from Medical_KG.ingestion.registry import available_sources, get_adapter

app = typer.Typer(help="Medical KG ingestion CLI")


def _load_batch(path: Path) -> Iterable[dict[str, Any]]:
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        yield json.loads(line)


@app.command("ingest")
def ingest(
    source: str = typer.Argument(..., help="Source identifier", autocompletion=lambda: available_sources()),
    batch: Path | None = typer.Option(None, help="Path to NDJSON with parameters"),
    auto: bool = typer.Option(False, help="Enable auto pipeline"),
    ledger_path: Path = typer.Option(Path(".ingest-ledger.jsonl"), help="Ledger storage"),
) -> None:
    """Run ingestion for the specified source."""

    if source not in available_sources():
        raise typer.BadParameter(f"Unknown source '{source}'. Known sources: {', '.join(available_sources())}")

    ledger = IngestionLedger(ledger_path)
    context = AdapterContext(ledger=ledger)
    client = AsyncHttpClient()
    adapter = get_adapter(source, context, client)

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
