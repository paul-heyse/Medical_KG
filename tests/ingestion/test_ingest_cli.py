import json
from pathlib import Path

from Medical_KG.cli import build_parser


def test_ingest_cli_batch(tmp_path: Path, monkeypatch) -> None:
    batch = tmp_path / "batch.ndjson"
    batch.write_text(json.dumps({"term": "lactate"}))
    ledger = tmp_path / "ledger.jsonl"

    parser = build_parser()
    args = parser.parse_args([
        "ingest",
        "pubmed",
        "--batch",
        str(batch),
        "--auto",
        "--ledger",
        str(ledger),
    ])

    class DummyAdapter:
        async def run(self, **kwargs):
            return []

    class DummyClient:
        async def aclose(self):
            return None

    monkeypatch.setattr("Medical_KG.cli.get_adapter", lambda *args, **kwargs: DummyAdapter())
    monkeypatch.setattr("Medical_KG.cli.AsyncHttpClient", lambda: DummyClient())
    result = args.func(args)
    assert result == 0
