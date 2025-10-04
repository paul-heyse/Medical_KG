from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.events import BatchProgress, DocumentCompleted, DocumentStarted
from Medical_KG.ingestion.ledger import IngestionLedger, LedgerState
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
        audit = self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.COMPLETED,
            metadata={"source": document.source},
            adapter=self.source,
        )
        return IngestionResult(
            document=document,
            state=audit.new_state,
            timestamp=datetime.fromtimestamp(audit.timestamp, tz=timezone.utc),
        )


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

    initial_results = pipeline.run("stub")
    assert initial_results[0].doc_ids == ["doc-1"]
    assert initial_results[0].failure_count == 1
    entry = ledger.get("doc-1")
    assert entry and entry.state is LedgerState.COMPLETED
    failed_entry = ledger.get("doc-2")
    assert failed_entry and failed_entry.state is LedgerState.FAILED

    # Resume should process only the previously failed record.
    results = pipeline.run("stub", resume=True)
    assert results[0].doc_ids == ["doc-2"]
    assert results[0].failure_count == 0
    assert adapter.parsed.count("doc-2") == 2


def test_pipeline_status_reports_entries(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = IngestionLedger(ledger_path)
    ledger.update_state("doc-a", LedgerState.COMPLETED, metadata={"source": "stub"})
    ledger.update_state("doc-b", LedgerState.FAILED, metadata={"error": "boom"})

    pipeline = IngestionPipeline(ledger, client_factory=lambda: _NoopClient())
    summary = pipeline.status()
    assert LedgerState.COMPLETED.value in summary
    assert summary[LedgerState.COMPLETED.value][0]["doc_id"] == "doc-a"
    assert LedgerState.FAILED.value in summary


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

    assert len(results) == 1
    assert results[0].doc_ids == ["doc-async"]


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


def test_stream_events_emit_lifecycle_events(tmp_path: Path) -> None:
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

    async def _collect() -> list[type[object]]:
        events = []
        async for event in pipeline.stream_events("stub", progress_interval=1):
            events.append(type(event))
        return events

    event_types = asyncio.run(_collect())
    assert event_types.count(DocumentStarted) == 2
    assert event_types.count(DocumentCompleted) == 2
    assert any(event_type is BatchProgress for event_type in event_types)


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
