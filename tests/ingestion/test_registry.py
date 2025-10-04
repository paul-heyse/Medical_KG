from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from Medical_KG.ingestion import registry
from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.ledger import IngestionLedger


def _ledger_path(tmp_path: Path) -> Path:
    target_dir = tmp_path / "ledger"
    target_dir.mkdir()
    return target_dir / "ledger.jsonl"


def test_available_sources_sorted() -> None:
    sources = registry.available_sources()
    assert sources == sorted(sources)
    assert "pubmed" in sources


def test_get_adapter_returns_instance(tmp_path: Path) -> None:
    ledger = IngestionLedger(_ledger_path(tmp_path))

    async def _build() -> str:
        async with AsyncHttpClient() as client:
            adapter = registry.get_adapter("pubmed", AdapterContext(ledger=ledger), client)
            return adapter.source

    assert asyncio.run(_build()) == "pubmed"


def test_get_adapter_unknown_source(tmp_path: Path) -> None:
    ledger = IngestionLedger(_ledger_path(tmp_path))

    async def _call() -> None:
        async with AsyncHttpClient() as client:
            registry.get_adapter("unknown", AdapterContext(ledger=ledger), client)

    with pytest.raises(ValueError):
        asyncio.run(_call())
