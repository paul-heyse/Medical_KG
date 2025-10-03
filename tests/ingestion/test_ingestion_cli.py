from __future__ import annotations

import asyncio
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

import pytest

# Provide a minimal typer shim for the CLI module.


class _TyperModule(types.ModuleType):
    Typer: type["_Typer"]
    Argument: Callable[..., object]
    Option: Callable[..., object]
    BadParameter: type[Exception]
    echo: Callable[[object], None]

    def __init__(self) -> None:
        super().__init__("typer")
        self.Typer = _Typer
        self.Argument = _argument
        self.Option = _option
        self.BadParameter = _BadParameter
        self.echo = _echo


class _BadParameter(Exception):
    pass


def _argument(default: object, **_kwargs: object) -> object:
    return default


def _option(default: object = None, **_kwargs: object) -> object:
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

from Medical_KG.ingestion import cli
from Medical_KG.ingestion.models import Document, IngestionResult

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

        class _Adapter:
            async def run(self, **params: object) -> list[IngestionResult]:
                calls.append(params)
                return results

        class _Registry:
            def available_sources(self) -> list[str]:
                return ["demo"]

            def get_adapter(self, _source: str, _context: object, _client: DummyClient) -> _Adapter:
                return _Adapter()

        monkeypatch.setattr(cli, "_resolve_registry", lambda: _Registry())
        return calls

    return _factory


def _result(doc_id: str) -> IngestionResult:
    document = Document(doc_id=doc_id, source="demo", content="{}")
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
    assert lines == [["doc-1", "doc-2"], ["doc-1", "doc-2"]]
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
    assert lines == [["doc-3"]]
    assert dummy_client.closed is True
    assert calls == [{}]


def test_ingest_rejects_unknown_source(make_registry: RegistryFactory) -> None:
    make_registry([])

    with pytest.raises(sys.modules["typer"].BadParameter):
        cli.ingest("unknown")
