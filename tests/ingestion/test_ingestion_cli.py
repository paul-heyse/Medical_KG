from __future__ import annotations

import json
from pathlib import Path
from collections.abc import AsyncIterator
from typing import Any, Callable

import pytest
from typer.testing import CliRunner

from Medical_KG.ingestion import cli
from Medical_KG.ingestion.cli_helpers import (
    BatchValidationError,
    chunk_parameters,
    count_ndjson_records,
    load_ndjson_batch,
)
from datetime import datetime, timezone

from Medical_KG.ingestion.events import BatchProgress, DocumentCompleted
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.pipeline import PipelineResult

runner = CliRunner()


class FakePipeline:
    def __init__(self, results: list[PipelineResult] | None = None) -> None:
        self.results = results or []
        self.calls: list[dict[str, Any]] = []
        self.stream_calls: list[dict[str, Any]] = []

    def run(
        self,
        source: str,
        params: Any = None,
        *,
        resume: bool,
    ) -> list[PipelineResult]:
        self.calls.append({"source": source, "params": params, "resume": resume})
        return list(self.results)

    async def stream_events(
        self,
        source: str,
        *,
        params: Any = None,
        resume: bool,
        **_: Any,
    ) -> AsyncIterator[DocumentCompleted | BatchProgress]:
        self.stream_calls.append({"source": source, "params": params, "resume": resume})
        completed = 0
        for result in self.results:
            for document in result.documents:
                completed += 1
                yield DocumentCompleted(
                    timestamp=0.0,
                    pipeline_id="test",
                    document=document,
                    duration=0.0,
                    adapter_metadata={},
                )
        yield BatchProgress(
            timestamp=0.0,
            pipeline_id="test",
            completed_count=completed,
            failed_count=0,
            in_flight_count=0,
            queue_depth=0,
            buffer_size=1,
            remaining=0,
            eta_seconds=None,
            backpressure_wait_seconds=0.0,
            backpressure_wait_count=0,
            checkpoint_doc_ids=[
                document.doc_id
                for result in self.results
                for document in result.documents
            ],
            is_checkpoint=True,
        )


def build_result(doc_ids: list[str]) -> PipelineResult:
    documents = [
        Document(doc_id=doc_id, source="demo", content="", metadata={})
        for doc_id in doc_ids
    ]
    now = datetime.now(timezone.utc)
    return PipelineResult(
        source="demo",
        documents=documents,
        errors=[],
        success_count=len(documents),
        failure_count=0,
        started_at=now,
        completed_at=now,
    )


@pytest.fixture(autouse=True)
def patch_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_available_sources", lambda: ["demo"])


@pytest.fixture
def make_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[list[PipelineResult]], FakePipeline]:
    def _factory(results: list[PipelineResult]) -> FakePipeline:
        pipeline = FakePipeline(results)
        monkeypatch.setattr(cli, "_build_pipeline", lambda _ledger: pipeline)
        return pipeline

    return _factory


def test_load_batch_skips_empty_lines(tmp_path: Path) -> None:
    batch = tmp_path / "batch.ndjson"
    batch.write_text("\n".join(['{"value": 1}', "", '{"value": 2}']))

    loaded = list(load_ndjson_batch(batch))
    assert loaded == [{"value": 1}, {"value": 2}]


def test_load_batch_rejects_invalid_json(tmp_path: Path) -> None:
    batch = tmp_path / "batch.ndjson"
    batch.write_text("{invalid json}")

    with pytest.raises(BatchValidationError) as excinfo:
        list(load_ndjson_batch(batch))

    assert "Invalid JSON" in str(excinfo.value)


def test_chunk_parameters(tmp_path: Path) -> None:
    items = [{"index": idx} for idx in range(5)]
    chunks = list(chunk_parameters(items, 2))
    assert chunks == [[{"index": 0}, {"index": 1}], [{"index": 2}, {"index": 3}], [{"index": 4}]]


def test_ingest_with_batch_runs_pipeline(
    tmp_path: Path, make_pipeline: Callable[[list[PipelineResult]], FakePipeline]
) -> None:
    results = [build_result(["doc-1", "doc-2"])]
    pipeline = make_pipeline(results)

    batch = tmp_path / "params.ndjson"
    batch.write_text("\n".join([json.dumps({"param": "value"}), json.dumps({"param": "second"})]))

    outcome = runner.invoke(
        cli.app,
        ["demo", "--batch", str(batch), "--summary-only", "--no-stream"],
    )
    assert outcome.exit_code == 0, outcome.stdout
    assert pipeline.calls[0]["params"] == [{"param": "value"}, {"param": "second"}]
    assert "Processed documents: 2" in outcome.stdout
    assert count_ndjson_records(batch) == 2


def test_ingest_auto_emits_doc_ids(
    tmp_path: Path, make_pipeline: Callable[[list[PipelineResult]], FakePipeline]
) -> None:
    results = [build_result(["doc-1", "doc-2"]), build_result(["doc-3"])]
    make_pipeline(results)

    batch = tmp_path / "params.ndjson"
    batch.write_text(json.dumps({"param": "value"}))

    outcome = runner.invoke(
        cli.app,
        ["demo", "--batch", str(batch), "--auto", "--no-stream"],
    )
    assert outcome.exit_code == 0, outcome.stdout
    lines = [json.loads(line) for line in outcome.stdout.splitlines() if line.startswith("[")]
    assert lines == [["doc-1", "doc-2"], ["doc-3"]]


def test_ingest_supports_json_output(
    tmp_path: Path, make_pipeline: Callable[[list[PipelineResult]], FakePipeline]
) -> None:
    results = [build_result(["doc-1"])]
    make_pipeline(results)
    batch = tmp_path / "params.ndjson"
    batch.write_text(json.dumps({"param": "value"}))

    outcome = runner.invoke(
        cli.app,
        ["demo", "--batch", str(batch), "--output", "json", "--no-stream"],
    )
    payload = json.loads(outcome.stdout)
    assert payload["adapter"] == "demo"
    assert payload["results"][0]["doc_ids"] == ["doc-1"]


def test_ingest_strict_validation_rejects_empty_batch(tmp_path: Path) -> None:
    batch = tmp_path / "empty.ndjson"
    batch.write_text("\n")

    outcome = runner.invoke(
        cli.app,
        ["demo", "--batch", str(batch), "--strict-validation", "--no-stream"],
    )
    assert outcome.exit_code == 2
    assert "Batch file is empty" in outcome.stderr


def test_dry_run_skips_pipeline_execution(
    tmp_path: Path, make_pipeline: Callable[[list[PipelineResult]], FakePipeline]
) -> None:
    pipeline = make_pipeline([])
    batch = tmp_path / "params.ndjson"
    batch.write_text(json.dumps({"param": "value"}))

    outcome = runner.invoke(
        cli.app,
        ["demo", "--batch", str(batch), "--dry-run", "--summary-only", "--no-stream"],
    )
    assert outcome.exit_code == 0
    assert pipeline.calls == []
    assert "Processed documents: 0" in outcome.stdout


def test_command_parsing_handles_multiple_flags(
    tmp_path: Path, make_pipeline: Callable[[list[PipelineResult]], FakePipeline]
) -> None:
    results = [build_result(["doc-1"])]
    pipeline = make_pipeline(results)
    batch = tmp_path / "params.ndjson"
    batch.write_text(json.dumps({"param": "value"}))

    outcome = runner.invoke(
        cli.app,
        [
            "demo",
            "--batch",
            str(batch),
            "--resume",
            "--limit",
            "1",
            "--auto",
            "--summary-only",
            "--output",
            "text",
            "--no-stream",
        ],
    )

    assert outcome.exit_code == 0, outcome.stdout
    assert pipeline.calls == [
        {
            "source": "demo",
            "params": [{"param": "value"}],
            "resume": True,
        }
    ]


def test_unknown_adapter_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_available_sources", lambda: ["other"])

    outcome = runner.invoke(cli.app, ["demo"])

    assert outcome.exit_code == 2
    assert "Unknown source" in outcome.stderr


def test_help_text_includes_examples() -> None:
    outcome = runner.invoke(cli.app, ["--help"])

    assert outcome.exit_code == 0
    assert "Unified ingestion interface" in outcome.stdout
    assert "Examples" in outcome.stdout
    assert "med ingest demo" in outcome.stdout
    assert "See also" in outcome.stdout


def test_adapter_help_lists_available_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_available_sources", lambda: ["demo", "umls"])

    outcome = runner.invoke(cli.app, ["--help"])

    assert "Available adapters: demo, umls" in outcome.stdout


def test_schema_validation_success(
    tmp_path: Path, make_pipeline: Callable[[list[PipelineResult]], FakePipeline]
) -> None:
    make_pipeline([build_result(["doc-1"])])
    batch = tmp_path / "params.ndjson"
    schema = tmp_path / "schema.json"
    batch.write_text(json.dumps({"param": "value"}))
    schema.write_text(json.dumps({"type": "object", "required": ["param"]}))

    outcome = runner.invoke(
        cli.app,
        [
            "demo",
            "--batch",
            str(batch),
            "--schema",
            str(schema),
            "--summary-only",
            "--no-stream",
        ],
    )

    assert outcome.exit_code == 0, outcome.stdout
    assert "validated against provided JSON schema" in outcome.stdout


def test_schema_validation_failure(tmp_path: Path) -> None:
    batch = tmp_path / "params.ndjson"
    schema = tmp_path / "schema.json"
    batch.write_text(json.dumps({"wrong": "value"}))
    schema.write_text(json.dumps({"type": "object", "required": ["param"]}))

    outcome = runner.invoke(
        cli.app,
        ["demo", "--batch", str(batch), "--schema", str(schema), "--no-stream"],
    )

    assert outcome.exit_code == 2
    assert "Schema validation failed" in outcome.stderr


def test_resume_sets_flag_on_pipeline(
    tmp_path: Path, make_pipeline: Callable[[list[PipelineResult]], FakePipeline]
) -> None:
    pipeline = make_pipeline([build_result(["doc-1"])])
    batch = tmp_path / "params.ndjson"
    batch.write_text(json.dumps({"param": "value"}))

    outcome = runner.invoke(
        cli.app,
        ["demo", "--batch", str(batch), "--resume", "--summary-only", "--no-stream"],
    )

    assert outcome.exit_code == 0
    assert pipeline.calls[0]["resume"] is True


def test_table_output_uses_rich_table(
    tmp_path: Path, make_pipeline: Callable[[list[PipelineResult]], FakePipeline]
) -> None:
    make_pipeline([build_result(["doc-1", "doc-2"])])
    batch = tmp_path / "params.ndjson"
    batch.write_text(json.dumps({"param": "value"}))

    outcome = runner.invoke(
        cli.app,
        ["demo", "--batch", str(batch), "--output", "table", "--no-stream"],
    )

    assert outcome.exit_code == 0, outcome.stdout
    assert "Processed documents" in outcome.stdout
    assert "doc-1" in outcome.stdout


def test_progress_reporting_advances(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []

    class _Progress:
        def __enter__(self) -> "_Progress":
            return self

        def __exit__(self, exc_type, exc, tb) -> None:
            return None

        def advance(self, task_id: int, value: int) -> None:
            calls.append(value)

    def _fake_create_progress(description: str, total: int | None) -> tuple[_Progress, int]:
        return _Progress(), 1

    monkeypatch.setattr(cli, "create_progress", _fake_create_progress)
    monkeypatch.setattr(cli, "should_display_progress", lambda force, quiet: True)

    pipeline = FakePipeline([build_result(["doc-1"]), build_result(["doc-2"])])
    monkeypatch.setattr(cli, "_build_pipeline", lambda _ledger: pipeline)

    batch = tmp_path / "batch.ndjson"
    batch.write_text(json.dumps({"param": "value"}))

    runner.invoke(
        cli.app,
        ["demo", "--batch", str(batch), "--summary-only", "--no-stream"],
    )

    assert calls, "progress advance should be invoked"


def test_error_for_missing_batch_file() -> None:
    outcome = runner.invoke(
        cli.app, ["demo", "--batch", "missing.ndjson", "--no-stream"]
    )

    assert outcome.exit_code == 2
    assert "Invalid value" in outcome.stderr


def test_stream_flag_emits_events(monkeypatch: pytest.MonkeyPatch) -> None:
    pipeline = FakePipeline([build_result(["doc-stream-1"])])
    monkeypatch.setattr(cli, "_build_pipeline", lambda _ledger: pipeline)

    outcome = runner.invoke(cli.app, ["demo", "--stream", "--summary-only"])

    assert outcome.exit_code == 0, outcome.stderr
    payloads = [json.loads(line) for line in outcome.stdout.splitlines() if line]
    assert any(item["type"] == "DocumentCompleted" for item in payloads)
    assert payloads[-1]["type"] == "BatchProgress"
    assert outcome.stderr
    assert "Processed documents" in outcome.stderr
    assert pipeline.stream_calls, "stream_events should be invoked"
