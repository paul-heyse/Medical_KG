from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from Medical_KG.ingestion.ledger import IngestionLedger
from Medical_KG.pdf import GpuNotAvailableError, MinerUConfig, MinerURunner, PdfDocument, PdfPipeline
from Medical_KG.pdf.gpu import CommandRunner, ensure_gpu


class StubRunner(CommandRunner):
    def __init__(self, returncode: int = 0) -> None:
        self.returncode = returncode
        self.commands: list[list[str]] = []

    def run(self, command: list[str]) -> subprocess.CompletedProcess[str]:
        self.commands.append(command)
        return subprocess.CompletedProcess(command, self.returncode, stdout="ok", stderr="")


def test_pdf_pipeline_updates_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REQUIRE_GPU", "0")
    monkeypatch.setattr("Medical_KG.pdf.gpu.detect_gpu", lambda runner=None: True)
    ledger_path = tmp_path / "ledger.jsonl"
    ledger = IngestionLedger(ledger_path)
    artifacts = tmp_path / "artifacts"
    runner = StubRunner()
    mineru = MinerURunner(MinerUConfig(output_dir=artifacts), runner=runner)
    pipeline = PdfPipeline(ledger=ledger, mineru=mineru)
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.0")
    document = PdfDocument(doc_key="DOC1", uri="http://example.com/doc.pdf", local_path=pdf_path)

    metadata = pipeline.process(document)

    assert ledger.get("DOC1").state == "pdf_ir_ready"
    assert "mineru_artifacts" in metadata
    assert runner.commands, "MinerU command should be invoked"


def test_ensure_gpu_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REQUIRE_GPU", "1")
    monkeypatch.setattr("Medical_KG.pdf.gpu.detect_gpu", lambda runner=None: False)
    with pytest.raises(GpuNotAvailableError):
        ensure_gpu(require_flag=True)
