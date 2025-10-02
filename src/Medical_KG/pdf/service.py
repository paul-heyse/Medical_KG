"""High-level PDF pipeline orchestration."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from Medical_KG.ingestion.ledger import IngestionLedger

from .gpu import ensure_gpu
from .mineru import MinerURunResult, MinerURunner
from .postprocess import HeaderFooterSuppressor, HyphenationRepair, SectionLabeler, TextBlock, TwoColumnReflow
from .qa import QaGateError, QaGates


@dataclass(slots=True)
class PdfDocument:
    doc_key: str
    uri: str
    local_path: Path


class ArtifactStore:
    def persist(self, doc_key: str, artifacts: Mapping[str, Path]) -> Mapping[str, str]:  # pragma: no cover - interface
        raise NotImplementedError


class LocalArtifactStore(ArtifactStore):
    def persist(self, doc_key: str, artifacts: Mapping[str, Path]) -> Mapping[str, str]:
        return {name: str(path) for name, path in artifacts.items()}


class PdfPipeline:
    def __init__(
        self,
        *,
        ledger: IngestionLedger,
        mineru: MinerURunner,
        artifacts: ArtifactStore | None = None,
        qa: QaGates | None = None,
    ) -> None:
        self._ledger = ledger
        self._mineru = mineru
        self._artifacts = artifacts or LocalArtifactStore()
        self._qa = qa or QaGates()
        self._reflow = TwoColumnReflow()
        self._suppressor = HeaderFooterSuppressor()
        self._hyphenation = HyphenationRepair()
        self._sections = SectionLabeler()

    def _load_blocks(self, run: MinerURunResult) -> Sequence[TextBlock]:
        # Placeholder implementation: in real pipeline we'd parse JSON
        return [TextBlock(page=1, y=100, text="Introduction"), TextBlock(page=1, y=200, text="Study overview")]

    def process(self, document: PdfDocument) -> Mapping[str, object]:
        ensure_gpu(require_flag=True)
        self._ledger.record(document.doc_key, "mineru_inflight")
        run = self._mineru.run(document.local_path, document.doc_key)
        blocks = self._load_blocks(run)
        if self._reflow.detect_columns(blocks):
            blocks = self._reflow.reflow(blocks)
        blocks = self._suppressor.suppress(blocks)
        blocks = [TextBlock(block.page, block.y, self._hyphenation.repair(block.text), block.label) for block in blocks]
        blocks = self._sections.label(blocks)
        metrics = self._qa.evaluate(blocks=blocks, confidences=[0.9], tables=[])
        artifact_map = self._artifacts.persist(
            document.doc_key,
            {
                "markdown_uri": run.artifacts.markdown,
                "blocks_uri": run.artifacts.blocks,
                "tables_uri": run.artifacts.tables,
            },
        )
        metadata = {
            "mineru_run_id": document.doc_key,
            "mineru_version": "v1",
            "mineru_cli_args": self._mineru.command(document.local_path, document.doc_key),
            "mineru_artifacts": artifact_map,
            "qa_metrics": asdict(metrics),
        }
        self._ledger.record(document.doc_key, "pdf_ir_ready", metadata)
        return metadata


__all__ = ["PdfPipeline", "PdfDocument", "ArtifactStore", "LocalArtifactStore"]
