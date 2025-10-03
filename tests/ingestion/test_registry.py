from __future__ import annotations

from collections.abc import AsyncIterator
import asyncio
from collections.abc import AsyncIterator
from typing import Any

import pytest

from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.registry import available_sources, get_adapter
from .fixtures import FakeLedger, make_adapter_context, sample_document_factory


class DummyAdapter(BaseAdapter):
    source = "dummy"

    def __init__(self, context: AdapterContext, records: list[dict[str, Any]]) -> None:
        super().__init__(context)
        self._records = records

    async def fetch(self) -> AsyncIterator[dict[str, Any]]:
        for record in self._records:
            yield record

    def parse(self, raw: dict[str, Any]) -> Document:
        if raw.get("error"):
            raise RuntimeError(raw["error"])
        content = raw.get("content", "")
        doc_id = self.build_doc_id(
            identifier=raw["id"],
            version=raw.get("version", "v1"),
            content=content.encode("utf-8"),
        )
        return Document(doc_id=doc_id, source=self.source, content=content, metadata={"id": raw["id"]}, raw=raw)

    def validate(self, document: Document) -> None:
        if document.metadata["id"] == "invalid":
            raise ValueError("invalid identifier")


def test_base_adapter_records_success_and_failure() -> None:
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    adapter = DummyAdapter(
        context,
        [
            {"id": "ok", "content": "value"},
            {"id": "invalid", "content": "bad"},
        ],
    )
    with pytest.raises(ValueError):
        asyncio.run(adapter.run())
    success = list(ledger.entries(state="auto_done"))
    failed = list(ledger.entries(state="auto_failed"))
    assert success and success[0].doc_id.startswith("dummy:ok")
    assert failed and "invalid identifier" in failed[0].metadata["error"]


def test_base_adapter_skips_completed_documents() -> None:
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    adapter = DummyAdapter(
        context,
        [
            {"id": "ok", "content": "value"},
        ],
    )
    first = asyncio.run(adapter.run())
    assert len(first) == 1
    second = asyncio.run(adapter.run())
    assert second == []
    all_entries = list(ledger.entries())
    assert len(all_entries) == 2
    assert {entry.state for entry in all_entries} == {"auto_inflight", "auto_done"}


def test_registry_lists_known_sources() -> None:
    sources = available_sources()
    assert "pubmed" in sources
    assert "clinicaltrials" in sources
    assert sources == sorted(sources)


def test_registry_returns_adapter_instance() -> None:
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = get_adapter("pubmed", context, client)
    try:
        assert adapter.source == "pubmed"
    finally:
        asyncio.run(client.aclose())


def test_sample_document_factory_builds_documents() -> None:
    factory = sample_document_factory("demo")
    document = factory("123", "payload", version="v2", extra="value")
    assert document.source == "demo"
    assert document.metadata["identifier"] == "123"
    assert document.metadata["extra"] == "value"
    assert document.doc_id.startswith("demo:123#v2")

