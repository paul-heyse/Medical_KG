import json
from pathlib import Path
from typing import Any

import pytest

from Medical_KG.cli import build_parser


def test_ingest_cli_batch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    batch = tmp_path / "batch.ndjson"
    batch.write_text(json.dumps({"term": "lactate"}))
    ledger = tmp_path / "ledger.jsonl"

    parser = build_parser()
    args = parser.parse_args(
        [
            "ingest",
            "pubmed",
            "--batch",
            str(batch),
            "--auto",
            "--ledger",
            str(ledger),
        ]
    )

    class DummyAdapter:
        async def run(self, **kwargs: Any) -> list[object]:
            return []

    class DummyClient:
        async def aclose(self) -> None:
            return None

    monkeypatch.setattr("Medical_KG.cli.get_adapter", lambda *args, **kwargs: DummyAdapter())
    monkeypatch.setattr("Medical_KG.cli.AsyncHttpClient", lambda: DummyClient())
    result = args.func(args)
    assert result == 0
