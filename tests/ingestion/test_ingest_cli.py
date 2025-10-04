import logging

import pytest

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


def test_ingest_translates_legacy_flags(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], caplog: pytest.LogCaptureFixture
) -> None:
    captured: dict[str, list[str]] = {}

    def fake_main(argv: list[str] | None = None) -> int:
        captured["argv"] = argv or []
        return 0

    monkeypatch.setattr("Medical_KG.ingestion.cli.main", fake_main)

    parser = build_parser()
    with caplog.at_level(logging.WARNING):
        args = parser.parse_args(
            [
                "ingest",
                "--source",
                "demo",
                "--batch-file",
                "params.ndjson",
                "--continue-from-ledger",
            ]
        )
        exit_code = args.func(args)

    assert exit_code == 0
    assert captured["argv"] == ["ingest", "demo", "--batch", "params.ndjson", "--resume"]
    stderr = capsys.readouterr().err
    assert "deprecated" in stderr
    assert any("Delegating ingestion command" in record.message for record in caplog.records)


def test_ingest_legacy_command_warns(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    captured: dict[str, list[str]] = {}

    def fake_main(argv: list[str] | None = None) -> int:
        captured["argv"] = argv or []
        return 0

    monkeypatch.setattr("Medical_KG.ingestion.cli.main", fake_main)

    parser = build_parser()
    args = parser.parse_args(["ingest-legacy", "--source", "demo"])
    exit_code = args.func(args)

    assert exit_code == 0
    assert captured["argv"] == ["ingest", "demo"]
    stderr = capsys.readouterr().err
    assert "deprecated" in stderr
