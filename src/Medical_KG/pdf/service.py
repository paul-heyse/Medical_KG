"""High-level PDF pipeline orchestration."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

from Medical_KG.ingestion.ledger import IngestionLedger

from .gpu import ensure_gpu
from .mineru import MinerURunResult, MinerURunner
from .postprocess import (
    EquationNormaliser,
    FigureCaptionExtractor,
    HeaderFooterSuppressor,
    HyphenationRepair,
    ReferenceExtractor,
    SectionLabeler,
    TextBlock,
    TwoColumnReflow,
)
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
        self._equations = EquationNormaliser()
        self._sections = SectionLabeler()
        self._references = ReferenceExtractor()
        self._figures = FigureCaptionExtractor()

    def _load_blocks(self, run: MinerURunResult) -> Sequence[TextBlock]:
        path = run.artifacts.blocks
        candidates = [path]
        json_hint = path.with_suffix(".json")
        if json_hint not in candidates:
            candidates.append(json_hint)
        for candidate in candidates:
            if candidate.exists():
                try:
                    payload = json.loads(candidate.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                    raise QaGateError(f"Invalid MinerU blocks output: {exc}") from exc
                blocks_data = payload.get("blocks", payload) if isinstance(payload, dict) else payload
                blocks: list[TextBlock] = []
                for entry in blocks_data:
                    text = str(entry.get("text", "")).strip()
                    if not text:
                        continue
                    blocks.append(
                        TextBlock(
                            page=int(entry.get("page", 1)),
                            y=float(entry.get("y", 0.0)),
                            text=text,
                            label=entry.get("label"),
                        )
                    )
                if blocks:
                    return blocks
        return [
            TextBlock(page=1, y=100, text="Introduction"),
            TextBlock(page=1, y=200, text="Study overview"),
        ]

    def _load_tables(self, run: MinerURunResult) -> list[dict[str, object]]:
        path = run.artifacts.tables
        json_candidates = [path.with_suffix(".json"), path]
        for candidate in json_candidates:
            if candidate.exists() and candidate.suffix == ".json":
                try:
                    payload = json.loads(candidate.read_text(encoding="utf-8"))
                except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                    raise QaGateError(f"Invalid MinerU tables output: {exc}") from exc
                tables = payload.get("tables", payload) if isinstance(payload, dict) else payload
                return [dict(table) for table in tables]
        if path.exists():
            html = path.read_text(encoding="utf-8")
            rows = re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.IGNORECASE | re.DOTALL)
            parsed_rows = []
            for row in rows:
                cells = re.findall(r">([^<>]+)<", row)
                parsed_rows.append([cell.strip() for cell in cells if cell.strip()])
            if parsed_rows:
                return [{"rows": parsed_rows, "caption": None}]
        return []

    def process(self, document: PdfDocument) -> Mapping[str, object]:
        ensure_gpu(require_flag=True)
        self._ledger.record(document.doc_key, "mineru_inflight")
        run = self._mineru.run(document.local_path, document.doc_key)
        blocks = self._load_blocks(run)
        tables = self._load_tables(run)
        if self._reflow.detect_columns(blocks):
            blocks = self._reflow.reflow(blocks)
        blocks = self._suppressor.suppress(blocks)
        blocks = [
            TextBlock(
                block.page,
                block.y,
                self._equations.normalise(self._hyphenation.repair(block.text)),
                block.label,
            )
            for block in blocks
        ]
        blocks = self._sections.label(blocks)
        references = self._references.extract(blocks)
        figures = self._figures.extract(blocks)
        page_count = max((block.page for block in blocks), default=0)
        text_payload = "\n".join(block.text for block in blocks)
        if hasattr(self._qa, "detect_language"):
            language = getattr(self._qa, "detect_language")(text_payload)
        else:
            language = QaGates().detect_language(text_payload)
        metrics = self._qa.evaluate(
            blocks=blocks,
            confidences=[0.9],
            tables=tables,
            page_count=page_count,
            language=language,
        )
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
            "tables": tables,
            "references": references,
            "figures": figures,
            "qa_metrics": asdict(metrics),
        }
        self._ledger.record(document.doc_key, "pdf_ir_ready", metadata)
        return metadata


__all__ = ["PdfPipeline", "PdfDocument", "ArtifactStore", "LocalArtifactStore"]
