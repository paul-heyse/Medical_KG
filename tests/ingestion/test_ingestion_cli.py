from __future__ import annotations

import asyncio
import json
import asyncio
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pytest

# Provide a minimal typer shim for the CLI module.
typer_stub = types.ModuleType("typer")


class _BadParameter(Exception):
    pass


class _Exit(SystemExit):
    def __init__(self, code: int = 0) -> None:
        super().__init__(code)


def _argument(default: object, **_kwargs: object) -> object:
    return default


def _option(*args: object, default: object = None, **_kwargs: object) -> object:
    return default if default is not None else (args[0] if args else None)


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
    typer_stub.Typer = _Typer
    typer_stub.Argument = _argument
    typer_stub.Option = _option
    typer_stub.BadParameter = _BadParameter
    typer_stub.Exit = _Exit
    typer_stub.echo = _echo
    sys.modules["typer"] = typer_stub

from Medical_KG.ingestion import cli
from Medical_KG.ingestion.models import IngestionResult
from .fixtures import FakeRegistry, sample_document_factory

RegistryFactory = Callable[[list[IngestionResult]], list[dict[str, object]]]


@pytest.fixture(autouse=True)
def reset_event_loop_policy() -> None:
    asyncio.set_event_loop_policy(asyncio.DefaultEventLoopPolicy())


class DummyClient:
    def __init__(self) -> None:
        self.closed = False

    async def aclose(self) -> None:
        self.closed = True


@pytest.fixture
def dummy_client(monkeypatch: pytest.MonkeyPatch) -> DummyClient:
    client = DummyClient()
    monkeypatch.setattr(cli, "AsyncHttpClient", lambda: client)
    return client


@pytest.fixture
def make_registry(monkeypatch: pytest.MonkeyPatch) -> RegistryFactory:
    def _factory(results: list[IngestionResult]) -> list[dict[str, object]]:
        calls: list[dict[str, object]] = []

        def _builder(_context: object, _client: DummyClient) -> Any:
            class _Adapter:
                async def run(self, **params: object) -> list[IngestionResult]:
                    calls.append(params)
                    return results

            return _Adapter()

        registry = FakeRegistry({"demo": _builder})
        monkeypatch.setattr(cli, "_resolve_registry", lambda: registry)
        return calls

    return _factory


_document_factory = sample_document_factory("demo")


def _result(doc_id: str) -> IngestionResult:
    document = _document_factory(doc_id, json.dumps({"doc": doc_id}))
    return IngestionResult(document=document, state="auto_done", timestamp=datetime.now(timezone.utc))


def test_load_batch_skips_empty_lines(tmp_path: Path) -> None:
    batch = tmp_path / "batch.ndjson"
    batch.write_text("\n".join(["{\"value\": 1}", "", "{\"value\": 2}"]))

    loaded = list(cli._load_batch(batch))
    assert loaded == [{"value": 1}, {"value": 2}]


def test_ingest_with_batch_outputs_doc_ids(
    dummy_client: DummyClient, make_registry: RegistryFactory, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    results = [_result("doc-1"), _result("doc-2")]
    calls = make_registry(results)

    batch = tmp_path / "batch.jsonl"
    batch.write_text("\n".join([json.dumps({"param": "value"}), json.dumps({"param": "second"})]))
    ledger_path = tmp_path / "ledger.jsonl"

    cli.ingest("demo", batch=batch, auto=True, ledger_path=ledger_path)

    captured = capsys.readouterr()
    lines = [json.loads(line) for line in captured.out.strip().splitlines() if line]
    expected_ids = [res.document.doc_id for res in results]
    assert lines == [expected_ids, expected_ids]
    assert dummy_client.closed is True
    assert calls == [{"param": "value"}, {"param": "second"}]


def test_ingest_without_batch_runs_once(
    dummy_client: DummyClient, make_registry: RegistryFactory, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    results = [_result("doc-3")]
    calls = make_registry(results)
    ledger_path = tmp_path / "ledger.jsonl"

    cli.ingest("demo", batch=None, auto=True, ledger_path=ledger_path)

    captured = capsys.readouterr()
    lines = [json.loads(line) for line in captured.out.strip().splitlines() if line]
    assert lines == [[results[0].document.doc_id]]
    assert dummy_client.closed is True
    assert calls == [{}]


def test_ingest_with_ids_runs_per_identifier(
    dummy_client: DummyClient, make_registry: RegistryFactory, tmp_path: Path
) -> None:
    results = [_result("doc-a"), _result("doc-b")]
    calls = make_registry(results)
    ledger_path = tmp_path / "ledger.jsonl"

    cli.ingest("demo", ids="alpha,beta", ledger_path=ledger_path)

    assert dummy_client.closed is True
    assert calls == [{"id": "alpha"}, {"id": "beta"}]


def test_ingest_rejects_unknown_source(make_registry: RegistryFactory) -> None:
    make_registry([])

    with pytest.raises(sys.modules["typer"].BadParameter):
        cli.ingest("unknown")


def test_ingest_rejects_conflicting_options(make_registry: RegistryFactory, tmp_path: Path) -> None:
    make_registry([])
    batch = tmp_path / "batch.jsonl"
    batch.write_text("{}\n")
    with pytest.raises(sys.modules["typer"].BadParameter):
        cli.ingest("demo", batch=batch, ids="dup")


def test_resume_retries_failed_tasks(
    dummy_client: DummyClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    attempts: dict[str, int] = {"alpha": 0, "beta": 0}
    results = {
        "alpha": [_result("doc-alpha")],
        "beta": [_result("doc-beta")],
    }

    def _builder(_context: object, _client: DummyClient) -> Any:
        class _Adapter:
            async def run(self, **params: object) -> list[IngestionResult]:
                identifier = params["id"]
                attempts[identifier] += 1
                if identifier == "alpha" and attempts[identifier] == 1:
                    raise RuntimeError("boom")
                return results[identifier]

        return _Adapter()

    registry = FakeRegistry({"demo": _builder})
    monkeypatch.setattr(cli, "_resolve_registry", lambda: registry)
    ledger_path = tmp_path / "ledger.jsonl"

    with pytest.raises(SystemExit) as exc:
        cli.ingest("demo", ids="alpha,beta", ledger_path=ledger_path)
    assert exc.value.code == 1
    cli.resume("demo", ledger_path=ledger_path)

    assert attempts == {"alpha": 2, "beta": 1}
    ledger = cli.IngestionLedger(ledger_path)
    task_states = {entry.doc_id: entry.state for entry in ledger.entries() if entry.doc_id.startswith("task:")}
    assert all(state == "cli_completed" for state in task_states.values())


def test_status_reports_summary(
    dummy_client: DummyClient, make_registry: RegistryFactory, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    results = [_result("doc-1")]
    make_registry(results)
    ledger_path = tmp_path / "ledger.jsonl"

    cli.ingest("demo", ledger_path=ledger_path)
    cli.status(ledger_path, format="json")

    output = capsys.readouterr().out.strip()
    payload = json.loads(output)
    assert payload["total"] >= 1
    assert payload["states"]["cli_completed"] >= 1
