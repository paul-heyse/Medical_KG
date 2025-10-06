from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

import pytest

import Medical_KG.ingestion.cli_helpers as cli_helpers
from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.cli_helpers import (
    BatchLoadError,
    LedgerResumeStats,
    format_cli_error,
    format_results,
    handle_ledger_resume,
    invoke_adapter_sync,
    load_ndjson_batch,
    should_display_progress,
)
from Medical_KG.ingestion.events import Document, PipelineResult
from Medical_KG.ingestion.ledger import IngestionLedger, LedgerState
from Medical_KG.ingestion.models import IngestionResult


class _StubAdapter(BaseAdapter):
    source = "stub"

    def __init__(self, context: AdapterContext, records: list[dict[str, Any]]) -> None:
        super().__init__(context)
        self._records = records

    async def fetch(self, *_: Any, **__: Any) -> Iterable[dict[str, Any]]:
        return self._records

    def parse(self, raw: dict[str, Any]) -> Document:
        return Document(
            doc_id=str(raw["id"]),
            source=self.source,
            content=json.dumps(raw),
            metadata={},
            raw=raw,
        )

    async def iter_results(self, **kwargs: Any) -> Iterable[IngestionResult]:
        for record in self._records:
            document = self.parse(record)
            yield IngestionResult(document=document, state=LedgerState.COMPLETED)


class _Registry:
    def __init__(self, adapter: _StubAdapter) -> None:
        self._adapter = adapter

    def get_adapter(self, source: str, context: AdapterContext, client: Any) -> BaseAdapter:
        return _StubAdapter(context, records=self._adapter._records)

    def available_sources(self) -> list[str]:
        return ["stub"]


class _Client:
    async def __aenter__(self) -> "_Client":
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def aclose(self) -> None:
        return None


def test_load_ndjson_batch_reads_objects(tmp_path: Path) -> None:
    batch = tmp_path / "batch.ndjson"
    batch.write_text("\n".join([json.dumps({"value": 1}), "", json.dumps({"value": 2})]))

    records = list(load_ndjson_batch(batch))
    assert records == [{"value": 1}, {"value": 2}]


def test_load_ndjson_batch_empty_file(tmp_path: Path) -> None:
    batch = tmp_path / "empty.ndjson"
    batch.write_text("")

    assert list(load_ndjson_batch(batch)) == []


def test_load_ndjson_batch_invalid_json(tmp_path: Path) -> None:
    batch = tmp_path / "broken.ndjson"
    batch.write_text("{" "invalid")

    with pytest.raises(BatchLoadError):
        list(load_ndjson_batch(batch))


def test_load_ndjson_batch_reports_progress(tmp_path: Path) -> None:
    batch = tmp_path / "progress.ndjson"
    batch.write_text("\n".join([json.dumps({"value": index}) for index in range(3)]))
    updates: list[tuple[int, int | None]] = []

    list(load_ndjson_batch(batch, progress=lambda count, total: updates.append((count, total))))
    assert updates == [(1, None), (2, None), (3, None)]


def test_invoke_adapter_collects_doc_ids(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    adapter = _StubAdapter(AdapterContext(ledger), records=[{"id": "doc-1"}, {"id": "doc-2"}])
    registry = _Registry(adapter)

    results = invoke_adapter_sync(
        "stub",
        ledger=ledger,
        registry=registry,
        client_factory=_Client,
    )

    assert len(results) == 1
    result = results[0]
    assert result.source == "stub"
    assert len(result.documents) == 2
    assert result.documents[0].doc_id == "doc-1"
    assert result.documents[1].doc_id == "doc-2"


def test_invoke_adapter_wraps_failures(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")

    class _BrokenRegistry:
        def get_adapter(self, *_: Any, **__: Any) -> BaseAdapter:
            raise RuntimeError("boom")

    # The pipeline swallows errors during streaming, so we get empty results
    results = invoke_adapter_sync(
        "stub", ledger=ledger, registry=_BrokenRegistry(), client_factory=_Client
    )
    # Should return one empty PipelineResult when adapter resolution fails
    assert len(results) == 1
    result = results[0]
    assert result.source == "stub"
    assert len(result.documents) == 0
    assert len(result.errors) == 0
    assert result.success_count == 0
    assert result.failure_count == 0


def test_format_cli_error_includes_remediation() -> None:
    exc = RuntimeError("bad things happened")
    rendered = format_cli_error(
        exc, prefix="Failure", remediation="Check configuration", use_color=False
    )
    assert "Failure" in rendered and "Check configuration" in rendered


def test_handle_ledger_resume_returns_stats(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    ledger.update_state("doc-1", LedgerState.COMPLETED)
    ledger.update_state("doc-2", LedgerState.FAILED)

    plan = handle_ledger_resume(ledger)
    assert plan.resume_ids == ["doc-2"]
    assert plan.stats == LedgerResumeStats(total=2, skipped=1, remaining=1)


def test_handle_ledger_resume_filters_candidates(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    ledger.update_state("doc-1", LedgerState.COMPLETED)

    plan = handle_ledger_resume(ledger, candidate_doc_ids=["doc-1", "doc-2"])
    assert plan.resume_ids == ["doc-2"]
    assert plan.skipped_ids == ["doc-1"]


def test_handle_ledger_resume_missing_file(tmp_path: Path) -> None:
    ledger_path = tmp_path / "missing-ledger.jsonl"
    plan = handle_ledger_resume(ledger_path)
    assert plan.resume_ids == []
    assert plan.stats == LedgerResumeStats(total=0, skipped=0, remaining=0)


def test_should_display_progress_defaults_to_tty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_helpers, "Progress", object())

    class _Stream:
        def isatty(self) -> bool:
            return True

    monkeypatch.setattr(cli_helpers, "sys", SimpleNamespace(stderr=_Stream()))
    assert should_display_progress(force=None, quiet=False) is True


def test_should_display_progress_respects_force(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_helpers, "Progress", object())

    class _Stream:
        def isatty(self) -> bool:
            return False

    monkeypatch.setattr(cli_helpers, "sys", SimpleNamespace(stderr=_Stream()))
    assert should_display_progress(force=True, quiet=False) is True
    assert should_display_progress(force=False, quiet=False) is False
    assert should_display_progress(force=None, quiet=True) is False


def test_format_results_jsonl() -> None:
    # Create mock documents with the expected doc_ids
    doc1 = Document(doc_id="doc-1", source="stub", content="content1", raw={"id": "doc-1"}, metadata={})
    doc2 = Document(doc_id="doc-2", source="stub", content="content2", raw={"id": "doc-2"}, metadata={})
    results = [PipelineResult(
        source="stub",
        documents=[doc1, doc2],
        errors=[],
        success_count=2,
        failure_count=0,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc)
    )]
    lines = format_results(results, output_format="jsonl")
    assert lines == [json.dumps(["doc-1", "doc-2"])]


def test_format_results_json() -> None:
    # Create mock document with the expected doc_id
    doc1 = Document(doc_id="doc-1", source="stub", content="content1", raw={"id": "doc-1"}, metadata={})
    results = [PipelineResult(
        source="stub",
        documents=[doc1],
        errors=[],
        success_count=1,
        failure_count=0,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc)
    )]
    payload = json.loads(format_results(results, output_format="json")[0])
    assert payload["documents"] == 1
    assert payload["results"][0]["source"] == "stub"


def test_format_results_text_verbose() -> None:
    # Create mock document with the expected doc_id
    doc1 = Document(doc_id="dóc-1", source="stub", content="content1", raw={"id": "dóc-1"}, metadata={})
    results = [PipelineResult(
        source="stub",
        documents=[doc1],
        errors=[],
        success_count=1,
        failure_count=0,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc)
    )]
    lines = format_results(results, verbose=True)
    assert "Batches processed" in lines[0]
    assert any("stub" in line for line in lines)
