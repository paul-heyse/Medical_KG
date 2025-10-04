from __future__ import annotations

from pathlib import Path
from typing import Dict, Mapping

import pytest

from Medical_KG.ingestion.ledger import LedgerAuditRecord, LedgerState, coerce_state
from Medical_KG.pdf.mineru import MinerUArtifacts, MinerURunResult
from Medical_KG.pdf.postprocess import TextBlock
from Medical_KG.pdf.qa import QaGates, QaMetrics
from Medical_KG.pdf.service import ArtifactStore, PdfDocument, PdfPipeline
from tests.fixtures.pdf_samples import (
    write_mineru_block_json,
    write_mineru_table_json,
    write_sample_pdf,
)


class RecordingLedger:
    def __init__(self) -> None:
        self.records: list[tuple[str, LedgerState, Mapping[str, object] | None]] = []

    def update_state(
        self,
        doc_key: str,
        state: LedgerState,
        *,
        metadata: Mapping[str, object] | None = None,
        **_: object,
    ) -> LedgerAuditRecord:
        self.records.append((doc_key, state, metadata))
        return LedgerAuditRecord(
            doc_id=doc_key,
            old_state=LedgerState.LEGACY,
            new_state=state,
            timestamp=0.0,
            adapter=None,
            metadata=dict(metadata or {}),
        )

    def record(
        self, doc_key: str, state: str, metadata: Mapping[str, object] | None = None
    ) -> LedgerAuditRecord:
        coerced = coerce_state(state)
        return self.update_state(doc_key, coerced, metadata=metadata)


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
        page_count: int | None = None,
        language: str | None = None,
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


def test_pdf_pipeline_end_to_end(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, pipeline_components: dict[str, object]
) -> None:
    monkeypatch.setenv("REQUIRE_GPU", "0")
    monkeypatch.setattr("Medical_KG.pdf.service.ensure_gpu", lambda require_flag=True: None)
    pdf_path = write_sample_pdf(tmp_path, "paper.pdf")
    document = PdfDocument(
        doc_key="DOC-001", uri="https://example.org/paper.pdf", local_path=pdf_path
    )

    pipeline = pipeline_components["pipeline"]
    metadata = pipeline.process(document)

    ledger: RecordingLedger = pipeline_components["ledger"]
    qa: RecordingQa = pipeline_components["qa"]
    artifact_store: RecordingArtifactStore = pipeline_components["artifact_store"]

    assert [state for _, state, _ in ledger.records] == [
        LedgerState.IR_BUILDING,
        LedgerState.IR_READY,
    ]
    assert metadata["mineru_artifacts"]["markdown_uri"].endswith("markdown.json")
    assert metadata["mineru_cli_args"][0] == "mineru"
    assert metadata["qa_metrics"]["reading_order_score"] == pytest.approx(0.95)
    assert metadata["references"] == []
    assert metadata["figures"] == []
    assert metadata["tables"] == []

    assert qa.blocks is not None
    block_texts = [block.text for block in qa.blocks]
    assert "Clinical Trial Header" not in block_texts
    assert "Background details" in block_texts
    assert any(block.label == "introduction" for block in qa.blocks)

    assert artifact_store.persisted[0][0] == "DOC-001"
    for stored_path in artifact_store.persisted[0][1].values():
        assert Path(stored_path).exists()


def test_pdf_pipeline_parses_blocks_tables_and_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("REQUIRE_GPU", "0")
    monkeypatch.setattr("Medical_KG.pdf.service.ensure_gpu", lambda require_flag=True: None)
    artifact_root = tmp_path / "mineru"
    artifact_root.mkdir()
    block_payload = [
        {"page": 1, "y": 40, "text": "Introduction"},
        {"page": 1, "y": 120, "text": "Study design"},
        {"page": 1, "y": 320, "text": "Figure 1. Patient flow"},
        {"page": 2, "y": 40, "text": "References"},
        {"page": 2, "y": 80, "text": "1. Smith J. Trial of aspirin."},
    ]
    table_payload = [
        {
            "caption": "Table 1",
            "rows": [["Arm", "Outcome"], ["Placebo", "10%"], ["Drug", "20%"]],
            "row_spans": [1, 1, 1],
            "col_spans": [1, 1],
        }
    ]
    write_mineru_block_json(artifact_root, block_payload, name="DOC-002/blocks.json")
    write_mineru_table_json(artifact_root, table_payload, name="DOC-002/tables.json")
    artifacts = MinerUArtifacts(
        markdown=artifact_root / "DOC-002" / "markdown.json",
        blocks=artifact_root / "DOC-002" / "blocks.json",
        tables=artifact_root / "DOC-002" / "tables.html",
        offset_map=artifact_root / "DOC-002" / "offset.json",
    )
    for path in (artifacts.markdown, artifacts.tables, artifacts.offset_map):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")
    result = MinerURunResult(doc_key="DOC-002", artifacts=artifacts, metadata={})

    class StubMinerU:
        def __init__(self, payload: MinerURunResult) -> None:
            self.payload = payload

        def command(self, pdf_path: Path, doc_key: str) -> list[str]:
            return ["mineru", "--input", str(pdf_path), "--id", doc_key]

        def run(self, pdf_path: Path, doc_key: str) -> MinerURunResult:
            return self.payload

    ledger = RecordingLedger()
    pipeline = PdfPipeline(
        ledger=ledger,
        mineru=StubMinerU(result),
        qa=QaGates(reading_order_threshold=0.0, min_pages=1, max_pages=5),
    )
    pdf_path = write_sample_pdf(tmp_path, "tables.pdf")
    metadata = pipeline.process(PdfDocument("DOC-002", "uri", pdf_path))

    assert metadata["references"] == [{"index": "1", "citation": "Smith J. Trial of aspirin."}]
    assert metadata["figures"] == [{"figure": "1", "caption": "Patient flow"}]
    assert metadata["tables"][0]["rows"][0] == ["Arm", "Outcome"]
    assert metadata["tables"][0]["caption"] == "Table 1"
    assert metadata["qa_metrics"]["table_count"] == 1


def test_pdf_pipeline_handles_multi_column_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("REQUIRE_GPU", "0")
    monkeypatch.setattr("Medical_KG.pdf.service.ensure_gpu", lambda require_flag=True: None)

    class ColumnMinerU(FakeMinerURunner):
        def run(self, pdf_path: Path, doc_key: str) -> MinerURunResult:  # type: ignore[override]
            result = super().run(pdf_path, doc_key)
            blocks_path = result.artifacts.blocks
            write_mineru_block_json(
                blocks_path.parent,
                [
                    {"page": 1, "y": 50, "text": "Methods"},
                    {"page": 1, "y": 80, "text": "Left column text"},
                    {"page": 1, "y": 350, "text": "Right column text"},
                ],
                name="blocks.json",
            )
            return result

    ledger = RecordingLedger()
    mineru = ColumnMinerU(tmp_path / "mineru")
    qa = RecordingQa()
    pipeline = PdfPipeline(ledger=ledger, mineru=mineru, qa=qa)
    pdf_path = write_sample_pdf(tmp_path, "columns.pdf")
    pipeline.process(PdfDocument("DOC-003", "uri", pdf_path))

    assert qa.blocks is not None
    assert [block.text for block in qa.blocks][:2] == ["Methods", "Left column text"]
