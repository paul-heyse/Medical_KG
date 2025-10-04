import json
from pathlib import Path

import pytest

from Medical_KG.cli import build_parser
from Medical_KG.ingestion.pipeline import PipelineResult


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

    monkeypatch.setattr(
        "Medical_KG.cli.invoke_adapter_sync",
        lambda *_, **__: [PipelineResult(source="pubmed", doc_ids=["doc-1"])],
    )
    result = args.func(args)
    assert result == 0
