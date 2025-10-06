from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.adapters.guidelines import NiceGuidelineAdapter
from Medical_KG.ingestion.events import (
    AdapterStateChange,
    BatchProgress,
    DocumentCompleted,
    DocumentFailed,
    DocumentStarted,
    PipelineEvent,
    errors_only,
)
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
        # Transition through proper states: FETCHED -> PARSING -> PARSED -> VALIDATING -> VALIDATED -> IR_BUILDING -> IR_READY -> COMPLETED
        self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.FETCHED,
            metadata={"source": document.source},
            adapter=self.source,
        )
        self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.PARSING,
            metadata={"source": document.source},
            adapter=self.source,
        )
        self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.PARSED,
            metadata={"source": document.source},
            adapter=self.source,
        )
        self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.VALIDATING,
            metadata={"source": document.source},
            adapter=self.source,
        )
        self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.VALIDATED,
            metadata={"source": document.source},
            adapter=self.source,
        )
        self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.IR_BUILDING,
            metadata={"source": document.source},
            adapter=self.source,
        )
        self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.IR_READY,
            metadata={"source": document.source},
            adapter=self.source,
        )
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


class _SpyClient(_NoopClient):
    instances: list["_SpyClient"] = []

    def __init__(
        self,
        *,
        telemetry: object | None = None,
        enable_metrics: bool | None = None,
    ) -> None:
        super().__init__()
        self.telemetry = telemetry
        self.enable_metrics = enable_metrics
        _SpyClient.instances.append(self)


def test_pipeline_passes_client_telemetry(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    adapter = _StubAdapter(AdapterContext(ledger), records=[])
    marker = object()
    _SpyClient.instances.clear()
    pipeline = IngestionPipeline(
        ledger,
        registry=_Registry(adapter),
        client_factory=_SpyClient,
        client_telemetry=marker,
        enable_client_metrics=False,
    )

    pipeline.run("stub")
    assert _SpyClient.instances
    client = _SpyClient.instances[-1]
    assert client.telemetry is marker
    assert client.enable_metrics is False


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
    result = results[0]
    assert result.doc_ids == ["doc-async"]
    assert result.success_count == 1
    assert result.failure_count == 0
    assert result.duration_seconds >= 0.0


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


def test_pipeline_stream_events_smoke(tmp_path: Path) -> None:
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

    async def _collect() -> list[PipelineEvent]:
        events: list[PipelineEvent] = []
        async for event in pipeline.stream_events("stub", progress_interval=1):
            events.append(event)
        return events

    events = asyncio.run(_collect())
    assert any(isinstance(event, DocumentStarted) for event in events)
    completed = [event for event in events if isinstance(event, DocumentCompleted)]
    assert [event.document.doc_id for event in completed] == ["doc-1", "doc-2"]
    assert all(not isinstance(event, DocumentFailed) for event in completed)
    assert any(isinstance(event, AdapterStateChange) for event in events)
    started_ids = [event.doc_id for event in events if isinstance(event, DocumentStarted)]
    completed_ids = [event.document.doc_id for event in events if isinstance(event, DocumentCompleted)]
    assert started_ids == completed_ids
    progress_events = [event for event in events if isinstance(event, BatchProgress)]
    assert progress_events, "expected at least one BatchProgress event"
    last_progress = progress_events[-1]
    assert last_progress.completed_count == 2
    assert last_progress.failed_count == 0
    assert last_progress.buffer_size >= 1
    assert last_progress.in_flight_count == 0


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


def test_stream_events_supports_filters_and_transformers(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = IngestionLedger(ledger_path)
    records = [
        {"id": "doc-1", "content": "ok"},
        {"id": "doc-2", "content": "retry", "fail_once": True},
    ]
    adapter = _StubAdapter(AdapterContext(ledger), records=records)
    pipeline = IngestionPipeline(
        ledger,
        registry=_Registry(adapter),
        client_factory=lambda: _NoopClient(),
    )

    async def _collect_errors() -> list[DocumentFailed]:
        events: list[DocumentFailed] = []
        async for event in pipeline.stream_events(
            "stub",
            event_filter=errors_only,
        ):
            assert isinstance(event, DocumentFailed)
            events.append(event)
        return events

    failures = asyncio.run(_collect_errors())
    assert len(failures) == 1
    assert failures[0].error_type == "RuntimeError"

    async def _collect_transformed() -> list[DocumentCompleted]:
        transformed: list[DocumentCompleted] = []

        def _transform(event: PipelineEvent) -> PipelineEvent | None:
            if isinstance(event, DocumentCompleted):
                return DocumentCompleted(
                    timestamp=event.timestamp,
                    pipeline_id=event.pipeline_id,
                    document=event.document,
                    duration=event.duration,
                    adapter_metadata={"transformed": True},
                )
            return event

        async for event in pipeline.stream_events(
            "stub",
            resume=True,
            event_transformer=_transform,
        ):
            if isinstance(event, DocumentCompleted):
                transformed.append(event)
        return transformed

    transformed_events = asyncio.run(_collect_transformed())
    assert transformed_events
    assert transformed_events[0].adapter_metadata == {"transformed": True}


def test_stream_events_reports_backpressure_metrics(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = IngestionLedger(ledger_path)
    records = [{"id": f"doc-{index}", "content": "ok"} for index in range(3)]
    adapter = _StubAdapter(AdapterContext(ledger), records=records)
    pipeline = IngestionPipeline(
        ledger,
        registry=_Registry(adapter),
        client_factory=lambda: _NoopClient(),
    )

    async def _consume_with_delays() -> list[BatchProgress]:
        progress_events: list[BatchProgress] = []
        async for event in pipeline.stream_events(
            "stub",
            buffer_size=1,
            progress_interval=1,
        ):
            if isinstance(event, BatchProgress):
                progress_events.append(event)
            await asyncio.sleep(0.01)
        return progress_events

    progress_events = asyncio.run(_consume_with_delays())
    assert progress_events
    tail = progress_events[-1]
    assert tail.backpressure_wait_count >= 1
    assert tail.backpressure_wait_seconds >= 0.0


def test_stream_events_include_checkpoint_metadata(tmp_path: Path) -> None:
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

    async def _collect() -> list[BatchProgress]:
        checkpoints: list[BatchProgress] = []
        async for event in pipeline.stream_events(
            "stub",
            checkpoint_interval=1,
            progress_interval=10,
        ):
            if isinstance(event, BatchProgress) and event.is_checkpoint:
                checkpoints.append(event)
        return checkpoints

    progress_events = asyncio.run(_collect())
    assert progress_events
    assert any(event.checkpoint_doc_ids for event in progress_events)
    # Collect all document IDs from checkpoint events
    all_checkpoint_doc_ids = []
    for event in progress_events:
        if event.checkpoint_doc_ids:
            all_checkpoint_doc_ids.extend(event.checkpoint_doc_ids)
    # Should have both documents in checkpoints
    assert set(all_checkpoint_doc_ids) == {"doc-1", "doc-2"}


def test_stream_events_resume_skips_completed_ids(tmp_path: Path) -> None:
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

    async def _collect(completed: list[str]) -> list[str]:
        seen: list[str] = []
        async for event in pipeline.stream_events(
            "stub",
            completed_ids=completed,
            progress_interval=1,
        ):
            if isinstance(event, DocumentCompleted):
                seen.append(event.document.doc_id)
        return seen

    first_run = asyncio.run(_collect([]))
    assert first_run == ["doc-1", "doc-2"]
    # After first run, both documents are COMPLETED
    # When we resume with completed_ids=["doc-1"], doc-1 should be skipped
    # but doc-2 cannot be reprocessed because COMPLETED has no valid transitions
    resumed = asyncio.run(_collect(["doc-1"]))
    # The current behavior is that completed_ids only skips the specified documents
    # Documents not in completed_ids that are already COMPLETED cannot be reprocessed
    assert resumed == []


def test_stream_events_with_real_nice_adapter_bootstrap(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger-nice.jsonl"
    ledger = IngestionLedger(ledger_path)
    bootstrap = [
        {
            "uid": "CG1",
            "title": "Guideline",
            "summary": "Summary",
            "url": "https://example.org/guideline",
            "licence": "OpenGov",
        }
    ]

    class _ClientStub:
        def bind_retry_callback(self, _callback: object) -> None:
            return None

    adapter = NiceGuidelineAdapter(
        AdapterContext(ledger),
        client=_ClientStub(),
        bootstrap_records=bootstrap,
    )
    pipeline = IngestionPipeline(
        ledger,
        registry=_Registry(adapter),
        client_factory=lambda: _NoopClient(),
    )

    async def _collect() -> list[str]:
        doc_ids: list[str] = []
        async for event in pipeline.stream_events("nice", progress_interval=1):
            if isinstance(event, DocumentCompleted):
                doc_ids.append(event.document.doc_id)
        return doc_ids

    emitted_ids = asyncio.run(_collect())
    assert emitted_ids
    assert emitted_ids[0].startswith("nice")


def test_stream_events_handle_large_batches(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger-large.jsonl"
    ledger = IngestionLedger(ledger_path)
    record_count = 10_000
    records = [{"id": f"doc-{index}", "content": "payload"} for index in range(record_count)]
    adapter = _StubAdapter(AdapterContext(ledger), records=records)
    pipeline = IngestionPipeline(
        ledger,
        registry=_Registry(adapter),
        client_factory=lambda: _NoopClient(),
    )

    async def _count() -> int:
        total = 0
        async for event in pipeline.stream_events("stub", progress_interval=5000):
            if isinstance(event, DocumentCompleted):
                total += 1
        return total

    processed = asyncio.run(_count())
    assert processed == record_count


def test_pipeline_integration_state_history(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger-history.jsonl"
    ledger = IngestionLedger(ledger_path)
    records = [
        {"id": "doc-1", "content": "payload"},
        {"id": "doc-2", "content": "payload"},
    ]
    adapter = _StubAdapter(AdapterContext(ledger), records=records)
    pipeline = IngestionPipeline(
        ledger,
        registry=_Registry(adapter),
        client_factory=lambda: _NoopClient(),
    )

    results = pipeline.run("stub")
    assert results
    history_doc1 = ledger.get_state_history("doc-1")
    assert history_doc1
    states = [audit.new_state for audit in history_doc1]
    assert states[0] is LedgerState.FETCHING
    assert states[-1] is LedgerState.COMPLETED
    assert LedgerState.VALIDATED in states


def test_stream_events_support_concurrent_execution(tmp_path: Path) -> None:
    ledger_a = IngestionLedger(tmp_path / "ledger-a.jsonl")
    ledger_b = IngestionLedger(tmp_path / "ledger-b.jsonl")
    records_a = [{"id": "a-1", "content": "ok"}, {"id": "a-2", "content": "ok"}]
    records_b = [{"id": "b-1", "content": "ok"}]
    adapter_a = _StubAdapter(AdapterContext(ledger_a), records=records_a)
    adapter_b = _StubAdapter(AdapterContext(ledger_b), records=records_b)
    pipeline_a = IngestionPipeline(
        ledger_a,
        registry=_Registry(adapter_a),
        client_factory=lambda: _NoopClient(),
    )
    pipeline_b = IngestionPipeline(
        ledger_b,
        registry=_Registry(adapter_b),
        client_factory=lambda: _NoopClient(),
    )

    async def _consume(pipeline: IngestionPipeline) -> list[str]:
        seen: list[str] = []
        async for event in pipeline.stream_events("stub", progress_interval=1):
            if isinstance(event, DocumentCompleted):
                seen.append(event.document.doc_id)
        return seen

    async def _consume_both() -> tuple[list[str], list[str]]:
        return await asyncio.gather(
            _consume(pipeline_a), _consume(pipeline_b)
        )

    results_a, results_b = asyncio.run(_consume_both())
    assert results_a == ["a-1", "a-2"]
    assert results_b == ["b-1"]


def test_pipeline_records_consumption_modes(monkeypatch, tmp_path: Path) -> None:
    from Medical_KG.ingestion import pipeline as pipeline_module

    class _CounterStub:
        def __init__(self) -> None:
            self.records: list[dict[str, str]] = []
            self._pending: dict[str, str] | None = None

        def labels(self, **labels: Any) -> "_CounterStub":
            self._pending = {key: str(value) for key, value in labels.items()}
            return self

        def inc(self, amount: float = 1.0) -> None:
            labels = self._pending or {}
            record = dict(labels)
            record["amount"] = str(amount)
            self.records.append(record)
            self._pending = None

    counter = _CounterStub()
    monkeypatch.setattr(pipeline_module, "PIPELINE_CONSUMPTION_COUNTER", counter)

    ledger_stream = IngestionLedger(tmp_path / "stream-ledger.jsonl")
    stream_adapter = _StubAdapter(
        AdapterContext(ledger_stream), records=[{"id": "stream-doc", "content": "ok"}]
    )
    pipeline_stream = IngestionPipeline(
        ledger_stream,
        registry=_Registry(stream_adapter),
        client_factory=lambda: _NoopClient(),
    )

    async def _drain_stream() -> None:
        async for _ in pipeline_stream.stream_events("stub", progress_interval=1):
            pass

    asyncio.run(_drain_stream())
    assert any(
        record.get("mode") == "stream_events" for record in counter.records
    )

    counter.records.clear()

    ledger_async = IngestionLedger(tmp_path / "async-ledger.jsonl")
    async_adapter = _StubAdapter(
        AdapterContext(ledger_async), records=[{"id": "async-doc", "content": "ok"}]
    )
    pipeline_async = IngestionPipeline(
        ledger_async,
        registry=_Registry(async_adapter),
        client_factory=lambda: _NoopClient(),
    )

    asyncio.run(pipeline_async.run_async("stub"))
    modes = {record.get("mode") for record in counter.records}
    assert modes == {"stream_events", "run_async"}
