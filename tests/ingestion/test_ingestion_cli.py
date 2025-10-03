# ruff: noqa: E402

from __future__ import annotations

import json
import sys
import tracemalloc
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, List

import pytest

# ---------------------------------------------------------------------------
# Typer shim for the ingestion CLI tests


class _TyperModule(types.ModuleType):
    Typer: type["_Typer"]
    Argument: Callable[..., object]
    Option: Callable[..., object]
    BadParameter: type[Exception]
    echo: Callable[[object], None]

    def __init__(self) -> None:  # pragma: no cover - infrastructure
        super().__init__("typer")
        self.Typer = _Typer
        self.Argument = _argument
        self.Option = _option
        self.BadParameter = _BadParameter
        self.echo = _echo


class _BadParameter(Exception):
    pass


def _argument(default: object, *_, **__) -> object:
    return default


def _option(default: object = None, *_, **__) -> object:
    return default


def _echo(value: object) -> None:
    print(value)


class _Typer:
    def __init__(self, **_kwargs: object) -> None:
        self._commands: dict[str, Callable[..., object]] = {}

    def command(self, name: str) -> Callable[[Callable[..., object]], Callable[..., object]]:
        def _decorator(func: Callable[..., object]) -> Callable[..., object]:
            self._commands[name] = func
            return func

        return _decorator


if "typer" not in sys.modules:
    sys.modules["typer"] = _TyperModule()


# ---------------------------------------------------------------------------
# Helper fixtures


from Medical_KG.ingestion import cli
from Medical_KG.ingestion.models import Document, IngestionResult
from Medical_KG.ingestion.pipeline import PipelineResult


class FakePipeline:
    def __init__(
        self,
        *,
        results: List[PipelineResult] | None = None,
        status: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        self.results = results or []
        self.status_payload = status or {}
        self.calls: list[dict[str, Any]] = []

    def run(self, source: str, params: Any = None, *, resume: bool) -> List[PipelineResult]:
        self.calls.append({"source": source, "params": params, "resume": resume})
        return self.results

    def status(self) -> dict[str, list[dict[str, Any]]]:
        return self.status_payload


@pytest.fixture
def make_pipeline(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[List[PipelineResult] | None, dict[str, list[dict[str, Any]]] | None], FakePipeline]:
    def _factory(
        results: List[PipelineResult] | None = None,
        status: dict[str, list[dict[str, Any]]] | None = None,
    ) -> FakePipeline:
        pipeline = FakePipeline(results=results, status=status)
        monkeypatch.setattr(cli, "_build_pipeline", lambda _ledger: pipeline)
        return pipeline

    return _factory


@pytest.fixture(autouse=True)
def mock_available_sources(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli, "_available_sources", lambda: ["demo"])


def _result(doc_id: str) -> IngestionResult:
    document = Document(doc_id=doc_id, source="demo", content="{}")
    return IngestionResult(
        document=document, state="auto_done", timestamp=datetime.now(timezone.utc)
    )


def _write_batch_file(path: Path, record_count: int) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for index in range(record_count):
            handle.write(json.dumps({"param": f"item-{index}"}) + "\n")


# ---------------------------------------------------------------------------
# Tests


def test_load_batch_skips_empty_lines(tmp_path: Path) -> None:
    batch = tmp_path / "batch.ndjson"
    batch.write_text("\n".join(['{"value": 1}', "", '{"value": 2}']))

    loaded = list(cli._load_batch(batch))
    assert loaded == [{"value": 1}, {"value": 2}]


def test_load_batch_rejects_invalid_json(tmp_path: Path) -> None:
    batch = tmp_path / "batch.ndjson"
    batch.write_text("{invalid json}")

    with pytest.raises(sys.modules["typer"].BadParameter) as excinfo:
        list(cli._load_batch(batch))

    assert "Invalid JSON" in str(excinfo.value)


def test_load_batch_rejects_non_mapping(tmp_path: Path) -> None:
    batch = tmp_path / "batch.ndjson"
    batch.write_text(json.dumps([1, 2, 3]))

    with pytest.raises(sys.modules["typer"].BadParameter) as excinfo:
        list(cli._load_batch(batch))

    assert "Batch entries must be" in str(excinfo.value)


def test_ingest_with_batch_outputs_doc_ids(
    make_pipeline: Callable[
        [List[PipelineResult] | None, dict[str, list[dict[str, Any]]] | None], FakePipeline
    ],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    results = [
        PipelineResult(source="demo", doc_ids=["doc-1", "doc-2"]),
        PipelineResult(source="demo", doc_ids=["doc-1", "doc-2"]),
    ]
    pipeline = make_pipeline(results, None)

    batch = tmp_path / "batch.jsonl"
    batch.write_text("\n".join([json.dumps({"param": "value"}), json.dumps({"param": "second"})]))
    ledger_path = tmp_path / "ledger.jsonl"

    cli.ingest("demo", batch=batch, auto=True, ledger_path=ledger_path, quiet=True)

    captured = capsys.readouterr()
    lines = [json.loads(line) for line in captured.out.strip().splitlines() if line]
    assert lines == [["doc-1", "doc-2"], ["doc-1", "doc-2"]]
    assert pipeline.calls[0]["params"] == [{"param": "value"}, {"param": "second"}]


def test_ingest_honours_chunk_size(
    make_pipeline: Callable[
        [List[PipelineResult] | None, dict[str, list[dict[str, Any]]] | None], FakePipeline
    ],
    tmp_path: Path,
) -> None:
    pipeline = make_pipeline([PipelineResult(source="demo", doc_ids=["doc-1"])], None)

    batch = tmp_path / "chunked.jsonl"
    batch.write_text(
        "\n".join(
            [
                json.dumps({"param": "first"}),
                json.dumps({"param": "second"}),
                json.dumps({"param": "third"}),
            ]
        )
    )

    cli.ingest("demo", batch=batch, ledger_path=tmp_path / "ledger.jsonl", chunk_size=2, quiet=True)

    assert len(pipeline.calls) == 2
    assert pipeline.calls[0]["params"] == [{"param": "first"}, {"param": "second"}]
    assert pipeline.calls[1]["params"] == [{"param": "third"}]


def test_ingest_large_batch_streams_in_chunks(
    make_pipeline: Callable[
        [List[PipelineResult] | None, dict[str, list[dict[str, Any]]] | None], FakePipeline
    ],
    tmp_path: Path,
) -> None:
    pipeline = make_pipeline([PipelineResult(source="demo", doc_ids=[])], None)

    batch = tmp_path / "large.jsonl"
    records = [json.dumps({"param": f"item-{index}"}) for index in range(2500)]
    batch.write_text("\n".join(records))

    cli.ingest("demo", batch=batch, ledger_path=tmp_path / "ledger.jsonl", chunk_size=500, quiet=True)

    assert len(pipeline.calls) == 5
    assert all(len(call["params"]) <= 500 for call in pipeline.calls)


def test_ingest_maintains_memory_profile_for_10k_records(
    make_pipeline: Callable[
        [List[PipelineResult] | None, dict[str, list[dict[str, Any]]] | None], FakePipeline
    ],
    tmp_path: Path,
) -> None:
    make_pipeline([PipelineResult(source="demo", doc_ids=[])], None)
    batch = tmp_path / "memory-10k.jsonl"
    _write_batch_file(batch, 10_000)

    tracemalloc.start()
    peak = 0
    try:
        cli.ingest("demo", batch=batch, ledger_path=tmp_path / "ledger.jsonl", chunk_size=1000, quiet=True)
    finally:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    assert peak < 25_000_000


def test_ingest_maintains_memory_profile_for_100k_records(
    make_pipeline: Callable[
        [List[PipelineResult] | None, dict[str, list[dict[str, Any]]] | None], FakePipeline
    ],
    tmp_path: Path,
) -> None:
    make_pipeline([PipelineResult(source="demo", doc_ids=[])], None)
    batch = tmp_path / "memory-100k.jsonl"
    _write_batch_file(batch, 100_000)

    tracemalloc.start()
    peak = 0
    try:
        cli.ingest("demo", batch=batch, ledger_path=tmp_path / "ledger.jsonl", chunk_size=1000, quiet=True)
    finally:
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    assert peak < 35_000_000


def test_ingest_reports_progress(
    make_pipeline: Callable[
        [List[PipelineResult] | None, dict[str, list[dict[str, Any]]] | None], FakePipeline
    ],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recorded: list[int] = []

    class _Progress:
        def __enter__(self) -> "_Progress":
            return self

        def __exit__(self, *_: object) -> None:
            return None

        def add_task(self, _description: str, total: int | None = None) -> int:
            self.total = total
            return 1

        def advance(self, _task_id: int, advance: int) -> None:
            recorded.append(advance)

    monkeypatch.setattr(cli, "_create_progress", lambda: _Progress())
    monkeypatch.setattr(cli, "_should_display_progress", lambda quiet: True)

    results = [
        PipelineResult(source="demo", doc_ids=["doc-1"]),
        PipelineResult(source="demo", doc_ids=["doc-2"]),
    ]
    make_pipeline(results, None)

    batch = tmp_path / "progress.jsonl"
    batch.write_text("\n".join([json.dumps({"param": "value"})]))

    cli.ingest("demo", batch=batch, ledger_path=tmp_path / "ledger.jsonl", quiet=False)

    assert recorded == [2]


def test_ingest_quiet_flag_skips_progress(
    make_pipeline: Callable[
        [List[PipelineResult] | None, dict[str, list[dict[str, Any]]] | None], FakePipeline
    ],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def _raise_progress() -> object:
        nonlocal called
        called = True
        raise AssertionError("progress should not be created when quiet")

    monkeypatch.setattr(cli, "_create_progress", _raise_progress)
    monkeypatch.setattr(cli, "_should_display_progress", lambda quiet: not quiet)

    make_pipeline([PipelineResult(source="demo", doc_ids=[])], None)
    batch = tmp_path / "quiet.jsonl"
    batch.write_text("\n".join([json.dumps({"param": "value"})]))

    cli.ingest("demo", batch=batch, ledger_path=tmp_path / "ledger.jsonl", quiet=True)

    assert called is False


def test_ingest_without_batch_runs_once(
    make_pipeline: Callable[
        [List[PipelineResult] | None, dict[str, list[dict[str, Any]]] | None], FakePipeline
    ],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    results = [PipelineResult(source="demo", doc_ids=["doc-3"])]
    pipeline = make_pipeline(results, None)
    ledger_path = tmp_path / "ledger.jsonl"

    cli.ingest("demo", batch=None, auto=True, ledger_path=ledger_path, quiet=True)

    captured = capsys.readouterr()
    lines = [json.loads(line) for line in captured.out.strip().splitlines() if line]
    assert lines == [["doc-3"]]
    assert pipeline.calls[0]["params"] is None


def test_ingest_rejects_unknown_source(make_pipeline: Callable[..., FakePipeline]) -> None:
    make_pipeline()
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(cli, "_available_sources", lambda: ["other"])
    with pytest.raises(sys.modules["typer"].BadParameter):
        cli.ingest("demo")
    monkeypatch.undo()


def test_ingest_accepts_ids_option(
    make_pipeline: Callable[
        [List[PipelineResult] | None, dict[str, list[dict[str, Any]]] | None], FakePipeline
    ],
) -> None:
    pipeline = make_pipeline([PipelineResult(source="demo", doc_ids=["doc-1"])], None)
    cli.ingest("demo", ids="NCT123,NCT456", quiet=True)
    assert pipeline.calls[0]["params"] == [{"ids": ["NCT123", "NCT456"]}]


def test_resume_invokes_pipeline_in_resume_mode(
    make_pipeline: Callable[
        [List[PipelineResult] | None, dict[str, list[dict[str, Any]]] | None], FakePipeline
    ],
    capsys: pytest.CaptureFixture[str],
) -> None:
    pipeline = make_pipeline([PipelineResult(source="demo", doc_ids=["doc-x"])], None)
    cli.resume("demo", auto=True, quiet=True)
    assert pipeline.calls[0]["resume"] is True
    captured = capsys.readouterr()
    assert json.loads(captured.out.strip()) == ["doc-x"]


def test_status_command_outputs_json(
    make_pipeline: Callable[
        [List[PipelineResult] | None, dict[str, list[dict[str, Any]]] | None], FakePipeline
    ],
    capsys: pytest.CaptureFixture[str],
) -> None:
    status_payload = {
        "auto_done": [{"doc_id": "doc-1", "metadata": {"source": "demo"}}],
        "auto_failed": [{"doc_id": "doc-2", "metadata": {"error": "boom"}}],
    }
    make_pipeline(None, status_payload)
    cli.status(fmt="json")
    captured = capsys.readouterr()
    assert json.loads(captured.out) == status_payload


def test_status_command_text_format(
    make_pipeline: Callable[..., FakePipeline], capsys: pytest.CaptureFixture[str]
) -> None:
    status_payload = {"auto_done": [{"doc_id": "doc-1", "metadata": {}}]}
    make_pipeline(None, status_payload)
    cli.status()
    captured = capsys.readouterr()
    assert "auto_done" in captured.out
