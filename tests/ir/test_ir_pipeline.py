from __future__ import annotations

from pathlib import Path

import pytest

from Medical_KG.ir.builder import (
    ClinicalTrialsBuilder,
    DailyMedBuilder,
    GuidelineBuilder,
    MinerUBuilder,
)
from Medical_KG.ir.models import Block
from Medical_KG.ir.normalizer import TextNormalizer
from Medical_KG.ir.storage import IrStorage
from Medical_KG.ir.validator import IRValidator, ValidationError


class _MemoryLedger:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, str]]] = []

    def record(self, doc_id: str, state: str, metadata: dict[str, str]) -> None:
        self.calls.append((doc_id, state, metadata))


def test_text_normalization_handles_dehyphenation() -> None:
    normalizer = TextNormalizer(dictionary={"treatment"})
    result = normalizer.normalize("treat-\nment improves outcomes\n\nNew paragraph")
    assert "treatment" in result.text
    assert result.language == "en"


def test_clinical_trials_builder_creates_blocks(tmp_path: Path) -> None:
    builder = ClinicalTrialsBuilder()
    study = {
        "title": "Trial Title",
        "status": "Completed",
        "eligibility": "Adults with sepsis",
        "outcomes": [
            {"measure": "Mortality", "description": "28 day", "timeFrame": "28 days"},
        ],
    }
    document = builder.build_from_study(
        doc_id="study#1", uri="https://clinicaltrials.gov/study#1", study=study
    )
    assert any(
        isinstance(block, Block) and block.section == "eligibility" for block in document.blocks
    )
    validator = IRValidator()
    validator.validate_document(document)
    storage = IrStorage(tmp_path)
    ledger = _MemoryLedger()
    path = storage.write(document, ledger=ledger)
    assert path.exists()
    assert any(state == "ir_written" for _, state, _ in ledger.calls)


def test_daily_med_builder_creates_loinc_blocks() -> None:
    builder = DailyMedBuilder()
    spl = {
        "sections": [
            {"loinc": "34084-4", "text": "Dosage guidelines"},
            {"loinc": "43683-2", "text": "Contraindications"},
        ],
        "ingredients": [
            {"name": "Drug", "strength": "5 mg", "basis": "per tablet"},
        ],
    }
    document = builder.build_from_spl(doc_id="spl#1", uri="https://dailymed/setid", spl=spl)
    assert {block.meta["loinc"] for block in document.blocks} == {"34084-4", "43683-2"}
    IRValidator().validate_document(document)


def test_mineru_builder_uses_offset_map() -> None:
    builder = MinerUBuilder()
    artifacts = {
        "markdown": "# Title\n\nParagraph text",
        "blocks": [
            {"type": "heading", "text": "Title", "section": "h1", "path": "0"},
            {"type": "paragraph", "text": "Paragraph text", "section": "body", "path": "1"},
        ],
        "tables": [
            {"caption": "Table 1", "headers": ["A"], "rows": [["B"]], "page": 1},
        ],
        "offset_map": [
            {
                "char_start": 0,
                "char_end": 5,
                "canonical_start": 0,
                "canonical_end": 5,
                "page": 1,
                "bbox": [0, 0, 10, 10],
            },
            {
                "char_start": 6,
                "char_end": 20,
                "canonical_start": 6,
                "canonical_end": 20,
                "page": 1,
                "bbox": [0, 10, 10, 20],
            },
        ],
    }
    document = builder.build_from_artifacts(
        doc_id="mineru#1", uri="s3://bucket/doc", artifacts=artifacts
    )
    assert document.span_map.to_list()[0]["page"] == 1
    IRValidator().validate_document(document)


def test_guideline_builder_parses_html() -> None:
    builder = GuidelineBuilder()
    html = """
    <html><body>
        <h1>Guideline Title</h1>
        <p>Recommendation paragraph.</p>
        <ul><li>List item</li></ul>
    </body></html>
    """
    document = builder.build_from_html(doc_id="guideline#1", uri="https://guideline", html=html)
    types = {block.type for block in document.blocks}
    assert types.issuperset({"heading", "paragraph", "list_item"})
    IRValidator().validate_document(document)


def test_validator_rejects_bad_span_map() -> None:
    builder = ClinicalTrialsBuilder()
    study = {"title": "Title", "status": "Active", "eligibility": "Patients"}
    document = builder.build_from_study(doc_id="study#2", uri="uri", study=study)
    document.span_map.add(10, 5, 10, 8, "invalid")
    with pytest.raises(ValidationError):
        IRValidator().validate_document(document)
