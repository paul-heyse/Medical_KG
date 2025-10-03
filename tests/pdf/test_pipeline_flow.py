from __future__ import annotations

from pathlib import Path
from typing import Dict, Mapping

import pytest

from Medical_KG.pdf.mineru import MinerUArtifacts, MinerURunResult
from Medical_KG.pdf.postprocess import TextBlock
from Medical_KG.pdf.qa import QaMetrics
from Medical_KG.pdf.service import ArtifactStore, PdfDocument, PdfPipeline


class RecordingLedger:
    def __init__(self) -> None:
        self.records: list[tuple[str, str, Mapping[str, object] | None]] = []

    def record(self, doc_key: str, state: str, metadata: Mapping[str, object] | None = None) -> None:
        self.records.append((doc_key, state, metadata))


class RecordingArtifactStore(ArtifactStore):
    def __init__(self, base: Path) -> None:
        self.base = base
        self.persisted: list[tuple[str, Mapping[str, Path]]] = []
        self.base.mkdir(parents=True, exist_ok=True)

    def persist(self, doc_key: str, artifacts: Mapping[str, Path]) -> Mapping[str, str]:
        self.persisted.append((doc_key, dict(artifacts)))
        stored: Dict[str, str] = {}
        for name, path in artifacts.items():
            destination = self.base / doc_key / Path(path).name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(f"copied:{path}", encoding="utf-8")
            stored[name] = str(destination)
        return stored


class RecordingQa:
    def __init__(self) -> None:
        self.blocks: list[TextBlock] | None = None

    def evaluate(
        self,
        *,
        blocks: list[TextBlock],
        confidences: list[float],
        tables: list[Mapping[str, object]],
    ) -> QaMetrics:
        self.blocks = blocks
        return QaMetrics(
            reading_order_score=0.95,
            ocr_confidence_mean=sum(confidences) / max(len(confidences), 1),
            table_count=len(tables),
            header_footer_suppressed=1,
        )


class FakeMinerURunner:
    def __init__(self, artifact_root: Path) -> None:
        self.artifact_root = artifact_root
        self.called_with: list[tuple[Path, str]] = []

    def command(self, pdf_path: Path, doc_key: str) -> list[str]:
        return ["mineru", "--input", str(pdf_path), "--id", doc_key]

    def run(self, pdf_path: Path, doc_key: str) -> MinerURunResult:
        self.called_with.append((pdf_path, doc_key))
        output_dir = self.artifact_root / doc_key
        output_dir.mkdir(parents=True, exist_ok=True)
        artifacts = MinerUArtifacts(
            markdown=output_dir / "markdown.json",
            blocks=output_dir / "blocks.json",
            tables=output_dir / "tables.html",
            offset_map=output_dir / "offset.json",
        )
        for path in (
            artifacts.markdown,
            artifacts.blocks,
            artifacts.tables,
            artifacts.offset_map,
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(path.name, encoding="utf-8")
        metadata = {"stdout": "ok", "stderr": ""}
        return MinerURunResult(doc_key=doc_key, artifacts=artifacts, metadata=metadata)


class CustomPdfPipeline(PdfPipeline):
    def _load_blocks(self, run: MinerURunResult) -> list[TextBlock]:  # type: ignore[override]
        return [
            TextBlock(page=1, y=15, text="Clinical Trial Header"),
            TextBlock(page=1, y=120, text="Introduction"),
            TextBlock(page=1, y=210, text="Back-\nground details"),
            TextBlock(page=1, y=360, text="Methods include randomization"),
            TextBlock(page=2, y=20, text="Clinical Trial Header"),
            TextBlock(page=2, y=120, text="Results"),
        ]


@pytest.fixture
def pipeline_components(tmp_path: Path) -> dict[str, object]:
    ledger = RecordingLedger()
    mineru = FakeMinerURunner(tmp_path / "mineru")
    artifact_store = RecordingArtifactStore(tmp_path / "artifacts")
    qa = RecordingQa()
    pipeline = CustomPdfPipeline(ledger=ledger, mineru=mineru, artifacts=artifact_store, qa=qa)
    return {
        "ledger": ledger,
        "mineru": mineru,
        "artifact_store": artifact_store,
        "qa": qa,
        "pipeline": pipeline,
    }


def test_pdf_pipeline_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pipeline_components: dict[str, object]) -> None:
    monkeypatch.setenv("REQUIRE_GPU", "0")
    monkeypatch.setattr("Medical_KG.pdf.service.ensure_gpu", lambda require_flag=True: None)
    pdf_path = tmp_path / "paper.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")
    document = PdfDocument(doc_key="DOC-001", uri="https://example.org/paper.pdf", local_path=pdf_path)

    pipeline = pipeline_components["pipeline"]
    metadata = pipeline.process(document)

    ledger: RecordingLedger = pipeline_components["ledger"]
    qa: RecordingQa = pipeline_components["qa"]
    artifact_store: RecordingArtifactStore = pipeline_components["artifact_store"]

    assert [state for _, state, _ in ledger.records] == ["mineru_inflight", "pdf_ir_ready"]
    assert metadata["mineru_artifacts"]["markdown_uri"].endswith("markdown.json")
    assert metadata["mineru_cli_args"][0] == "mineru"
    assert metadata["qa_metrics"]["reading_order_score"] == pytest.approx(0.95)

    assert qa.blocks is not None
    block_texts = [block.text for block in qa.blocks]
    assert "Clinical Trial Header" not in block_texts
    assert "Background details" in block_texts
    assert any(block.label == "introduction" for block in qa.blocks)

    assert artifact_store.persisted[0][0] == "DOC-001"
    for stored_path in artifact_store.persisted[0][1].values():
        assert Path(stored_path).exists()
