from __future__ import annotations

import pytest

from Medical_KG import cli as root_cli
from Medical_KG.cli import build_parser


def test_ingest_delegates_to_unified_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, list[str]] = {}

    def fake_main(argv: list[str] | None = None) -> int:
        captured["argv"] = argv or []
        return 0

    monkeypatch.setattr("Medical_KG.ingestion.cli.main", fake_main)

    parser = build_parser()
    args = parser.parse_args(["ingest", "demo", "--batch", "payload.ndjson"])
    exit_code = args.func(args)

    assert exit_code == 0
    assert captured["argv"] == ["ingest", "demo", "--batch", "payload.ndjson"]


def test_ingest_passes_arguments_without_translation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    captured: dict[str, list[str]] = {}

    def fake_main(argv: list[str] | None = None) -> int:
        captured["argv"] = argv or []
        return 0

    monkeypatch.setattr("Medical_KG.ingestion.cli.main", fake_main)

    parser = build_parser()
    args = parser.parse_args(
        ["ingest", "--source", "demo", "--batch-file", "params.ndjson", "--continue-from-ledger"]
    )
    exit_code = args.func(args)

    assert exit_code == 0
    assert captured["argv"] == [
        "ingest",
        "--source",
        "demo",
        "--batch-file",
        "params.ndjson",
        "--continue-from-ledger",
    ]
    captured_output = capsys.readouterr()
    assert captured_output.err == ""


def test_cli_main_routes_ingest_command(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, list[str]] = {}

    def fake_main(argv: list[str] | None = None) -> int:
        captured["argv"] = argv or []
        return 0

    monkeypatch.setattr("Medical_KG.ingestion.cli.main", fake_main)
    exit_code = root_cli.main([
        "ingest",
        "demo",
        "--batch",
        "payload.ndjson",
    ])

    assert exit_code == 0
    assert captured["argv"] == ["ingest", "demo", "--batch", "payload.ndjson"]
