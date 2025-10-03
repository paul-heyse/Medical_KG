from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Iterable

import pytest

from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.ledger import IngestionLedger
from Medical_KG.ingestion.models import Document, IngestionResult
from Medical_KG.ingestion.pipeline import IngestionPipeline, PipelineResult


class _StubAdapter(BaseAdapter):
    source = "stub"

    def __init__(self, context: AdapterContext, *, records: list[dict[str, Any]]) -> None:
        super().__init__(context)
        self._records = list(records)
        self._fail_once: dict[str, bool] = {
            record["id"]: record.get("fail_once", False) for record in records
        }
        self.parsed: list[str] = []

    async def fetch(self, *_: Any, resume: bool = False, **__: Any) -> Iterable[dict[str, Any]]:
        for record in self._records:
            yield record

    def parse(self, raw: dict[str, Any]) -> Document:
        identifier = raw["id"]
        self.parsed.append(identifier)
        return Document(
            doc_id=identifier,
            source=self.source,
            content=raw.get("content", ""),
            metadata={},
            raw=raw,
        )

    def validate(self, document: Document) -> None:
        if self._fail_once.get(document.doc_id):
            self._fail_once[document.doc_id] = False
            raise RuntimeError("transient failure")

    async def write(self, document: Document) -> IngestionResult:
        entry = self.context.ledger.record(
            doc_id=document.doc_id,
            state="auto_done",
            metadata={"source": document.source},
        )
        return IngestionResult(document=document, state=entry.state, timestamp=entry.timestamp)


class _Registry:
    def __init__(self, adapter: _StubAdapter) -> None:
        self._adapter = adapter

    def get_adapter(self, source: str, context: AdapterContext, client: Any) -> BaseAdapter:
        return self._adapter


class _NoopClient:
    async def __aenter__(self) -> "_NoopClient":
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: BaseException | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:  # pragma: no cover - interface completeness
        return None


def test_pipeline_resume_skips_completed(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = IngestionLedger(ledger_path)
    records = [
        {"id": "doc-1", "content": "ok"},
        {"id": "doc-2", "content": "retry", "fail_once": True},
    ]
    adapter = _StubAdapter(AdapterContext(ledger), records=records)
    pipeline = IngestionPipeline(
        ledger, registry=_Registry(adapter), client_factory=lambda: _NoopClient()
    )

    with pytest.raises(RuntimeError):
        pipeline.run("stub")
    entry = ledger.get("doc-1")
    assert entry and entry.state == "auto_done"
    failed_entry = ledger.get("doc-2")
    assert failed_entry and failed_entry.state == "auto_failed"

    # Resume should process only the previously failed record.
    results = pipeline.run("stub", resume=True)
    assert results[0].doc_ids == ["doc-2"]
    assert adapter.parsed.count("doc-2") == 2


def test_pipeline_status_reports_entries(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = IngestionLedger(ledger_path)
    ledger.record("doc-a", "auto_done", {"source": "stub"})
    ledger.record("doc-b", "auto_failed", {"error": "boom"})

    pipeline = IngestionPipeline(ledger, client_factory=lambda: _NoopClient())
    summary = pipeline.status()
    assert "auto_done" in summary and summary["auto_done"][0]["doc_id"] == "doc-a"
    assert "auto_failed" in summary


def test_pipeline_run_async_supports_event_loops(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = IngestionLedger(ledger_path)
    records = [{"id": "doc-async", "content": "ok"}]
    adapter = _StubAdapter(AdapterContext(ledger), records=records)
    pipeline = IngestionPipeline(
        ledger,
        registry=_Registry(adapter),
        client_factory=lambda: _NoopClient(),
    )

    async def _invoke() -> list[PipelineResult]:
        return await pipeline.run_async("stub")

    loop = asyncio.new_event_loop()
    try:
        results = loop.run_until_complete(_invoke())
    finally:
        loop.close()

    assert results == [PipelineResult(source="stub", doc_ids=["doc-async"])]


def test_pipeline_iter_results_streams_documents(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = IngestionLedger(ledger_path)
    records = [
        {"id": "doc-1", "content": "ok"},
        {"id": "doc-2", "content": "ok"},
    ]
    adapter = _StubAdapter(AdapterContext(ledger), records=records)
    pipeline = IngestionPipeline(
        ledger,
        registry=_Registry(adapter),
        client_factory=lambda: _NoopClient(),
    )

    async def _collect() -> list[str]:
        stream = pipeline.iter_results("stub")
        return [document.doc_id async for document in stream]

    doc_ids = asyncio.run(_collect())
    assert doc_ids == ["doc-1", "doc-2"]


def test_pipeline_iter_results_closes_client_on_cancel(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = IngestionLedger(ledger_path)
    records = [{"id": "doc-1", "content": "ok"}]
    adapter = _StubAdapter(AdapterContext(ledger), records=records)

    class _Client:
        def __init__(self) -> None:
            self.closed = False

        async def __aenter__(self) -> "_Client":
            return self

        async def __aexit__(
            self,
            exc_type: type[BaseException] | None,
            exc: BaseException | None,
            tb: BaseException | None,
        ) -> None:
            await self.aclose()

        async def aclose(self) -> None:
            self.closed = True

    client = _Client()
    pipeline = IngestionPipeline(
        ledger,
        registry=_Registry(adapter),
        client_factory=lambda: client,
    )

    async def _consume_one() -> bool:
        stream = pipeline.iter_results("stub")
        agen = stream.__aiter__()
        await agen.__anext__()
        await agen.aclose()
        return client.closed

    closed = asyncio.run(_consume_one())
    assert closed is True
