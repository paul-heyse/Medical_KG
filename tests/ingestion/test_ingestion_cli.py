from __future__ import annotations

import json
from pathlib import Path
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
from Medical_KG.ingestion.pipeline import PipelineResult

runner = CliRunner()


class FakePipeline:
    def __init__(self, results: list[PipelineResult] | None = None) -> None:
        self.results = results or []
        self.calls: list[dict[str, Any]] = []

    def run(
        self,
        source: str,
        params: Any = None,
        *,
        resume: bool,
    ) -> list[PipelineResult]:
        self.calls.append({"source": source, "params": params, "resume": resume})
        return list(self.results)


@pytest.fixture(autouse=True)
def patch_adapters(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_available_sources", lambda: ["demo"])


@pytest.fixture
def make_pipeline(monkeypatch: pytest.MonkeyPatch) -> Callable[[list[PipelineResult]], FakePipeline]:
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
    results = [PipelineResult(source="demo", doc_ids=["doc-1", "doc-2"])]
    pipeline = make_pipeline(results)

    batch = tmp_path / "params.ndjson"
    batch.write_text("\n".join([json.dumps({"param": "value"}), json.dumps({"param": "second"})]))

    outcome = runner.invoke(
        cli.app,
        ["demo", "--batch", str(batch), "--summary-only"],
    )
    assert outcome.exit_code == 0, outcome.stdout
    assert pipeline.calls[0]["params"] == [{"param": "value"}, {"param": "second"}]
    assert "Processed documents: 2" in outcome.stdout
    assert count_ndjson_records(batch) == 2


def test_ingest_auto_emits_doc_ids(
    tmp_path: Path, make_pipeline: Callable[[list[PipelineResult]], FakePipeline]
) -> None:
    results = [
        PipelineResult(source="demo", doc_ids=["doc-1", "doc-2"]),
        PipelineResult(source="demo", doc_ids=["doc-3"]),
    ]
    make_pipeline(results)

    batch = tmp_path / "params.ndjson"
    batch.write_text(json.dumps({"param": "value"}))

    outcome = runner.invoke(
        cli.app,
        ["demo", "--batch", str(batch), "--auto"],
    )
    assert outcome.exit_code == 0, outcome.stdout
    lines = [json.loads(line) for line in outcome.stdout.splitlines() if line.startswith("[")]
    assert lines == [["doc-1", "doc-2"], ["doc-3"]]


def test_ingest_supports_json_output(
    tmp_path: Path, make_pipeline: Callable[[list[PipelineResult]], FakePipeline]
) -> None:
    results = [PipelineResult(source="demo", doc_ids=["doc-1"])]
    make_pipeline(results)
    batch = tmp_path / "params.ndjson"
    batch.write_text(json.dumps({"param": "value"}))

    outcome = runner.invoke(
        cli.app,
        ["demo", "--batch", str(batch), "--output", "json"],
    )
    payload = json.loads(outcome.stdout)
    assert payload["adapter"] == "demo"
    assert payload["results"][0]["doc_ids"] == ["doc-1"]


def test_ingest_strict_validation_rejects_empty_batch(tmp_path: Path) -> None:
    batch = tmp_path / "empty.ndjson"
    batch.write_text("\n")

    outcome = runner.invoke(
        cli.app,
        ["demo", "--batch", str(batch), "--strict-validation"],
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
        ["demo", "--batch", str(batch), "--dry-run", "--summary-only"],
    )
    assert outcome.exit_code == 0
    assert pipeline.calls == []
    assert "Processed documents: 0" in outcome.stdout
