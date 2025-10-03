from __future__ import annotations

import asyncio

import pytest

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.ledger import IngestionLedger
from Medical_KG.ingestion import registry


def test_available_sources_sorted() -> None:
    sources = registry.available_sources()
    assert sources == sorted(sources)
    assert "pubmed" in sources


def test_get_adapter_returns_instance(tmp_path: pytest.TempPathFactory) -> None:
    ledger = IngestionLedger(tmp_path.mktemp("ledger") / "ledger.jsonl")
    client = AsyncHttpClient()
    adapter = registry.get_adapter("pubmed", AdapterContext(ledger=ledger), client)
    assert adapter.source == "pubmed"
    asyncio.run(client.aclose())


def test_get_adapter_unknown_source(tmp_path: pytest.TempPathFactory) -> None:
    ledger = IngestionLedger(tmp_path.mktemp("ledger") / "ledger.jsonl")
    client = AsyncHttpClient()
    with pytest.raises(ValueError):
        registry.get_adapter("unknown", AdapterContext(ledger=ledger), client)
    asyncio.run(client.aclose())
