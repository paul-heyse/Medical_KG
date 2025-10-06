from __future__ import annotations

from pathlib import Path

import pytest

from Medical_KG.ingestion.ledger import LedgerState
from Medical_KG.ingestion.types import (
    ClinicalDocumentPayload,
    DailyMedDocumentPayload,
    NiceGuidelineDocumentPayload,
    WhoGhoDocumentPayload,
)
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

CLINICAL_RAW: ClinicalDocumentPayload = {
    "nct_id": "NCT-PIPELINE-1",
    "title": "Trial Title",
    "version": "v1",
    "arms": [],
    "eligibility": "Adults with sepsis",
    "outcomes": [],
}

DAILY_MED_RAW: DailyMedDocumentPayload = {
    "setid": "SET123",
    "title": "Drug Label",
    "version": "2024-01-01",
    "sections": [
        {"loinc": "34084-4", "text": "Dosage guidelines"},
        {"loinc": "43683-2", "text": "Contraindications"},
    ],
}

GUIDELINE_RAW: NiceGuidelineDocumentPayload = {
    "uid": "NG123",
    "title": "Guideline Title",
    "summary": "Recommendation paragraph.",
    "url": "https://guideline",
}

WHO_RAW: WhoGhoDocumentPayload = {
    "value": 1.23,
    "indicator": "life_expectancy",
    "country": "US",
    "year": "2024",
}


class _MemoryLedger:
    def __init__(self) -> None:
        self.calls: list[tuple[str, LedgerState, dict[str, str]]] = []

    def record(self, doc_id: str, state: LedgerState, metadata: dict[str, str]) -> None:
        if not isinstance(state, LedgerState):
            raise TypeError("state must be a LedgerState instance")
        self.calls.append((doc_id, state, metadata))

    def update_state(
        self,
        doc_id: str,
        state: LedgerState,
        *,
        metadata: dict[str, str] | None = None,
        **_: object,
    ) -> None:
        self.record(doc_id, state, metadata or {})


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
    document.provenance["nct_id"] = CLINICAL_RAW["nct_id"]
    document.metadata.update(
        {
            "payload_family": "clinical",
            "payload_type": "clinical_document",
            "identifier": CLINICAL_RAW["nct_id"],
            "title": CLINICAL_RAW["title"],
            "version": CLINICAL_RAW["version"],
        }
    )
    assert any(
        isinstance(block, Block) and block.section == "eligibility" for block in document.blocks
    )
    validator = IRValidator()
    validator.validate_document(document, raw=CLINICAL_RAW)
    storage = IrStorage(tmp_path)
    ledger = _MemoryLedger()
    path = storage.write(document, ledger=ledger)
    assert path.exists()
    assert any(state is LedgerState.IR_READY for _, state, _ in ledger.calls)


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
    document.metadata.update(
        {
            "payload_family": "clinical",
            "payload_type": "dailymed",
            "identifier": DAILY_MED_RAW["setid"],
            "title": DAILY_MED_RAW["title"],
            "version": DAILY_MED_RAW["version"],
        }
    )
    IRValidator().validate_document(document, raw=DAILY_MED_RAW)


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
    document.metadata.update(
        {
            "payload_family": "knowledge_base",
            "payload_type": "who_gho",
            "indicator": WHO_RAW["indicator"],
            "value": WHO_RAW["value"],
            "country": WHO_RAW["country"],
            "version": WHO_RAW["year"],
        }
    )
    IRValidator().validate_document(document, raw=WHO_RAW)


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
    document.provenance["guideline"] = {"uid": GUIDELINE_RAW["uid"], "url": GUIDELINE_RAW["url"]}
    document.metadata.update(
        {
            "payload_family": "guideline",
            "payload_type": "nice_guideline",
            "identifier": GUIDELINE_RAW["uid"],
            "title": GUIDELINE_RAW["title"],
            "summary": GUIDELINE_RAW["summary"],
            "source_url": GUIDELINE_RAW["url"],
        }
    )
    IRValidator().validate_document(document, raw=GUIDELINE_RAW)


def test_validator_rejects_bad_span_map() -> None:
    builder = ClinicalTrialsBuilder()
    study = {"title": "Title", "status": "Active", "eligibility": "Patients"}
    document = builder.build_from_study(doc_id="study#2", uri="uri", study=study)
    document.span_map.add(10, 5, 10, 8, "invalid")
    with pytest.raises(ValidationError):
        document.metadata.update(
            {
                "payload_family": "clinical",
                "payload_type": "clinical_document",
                "identifier": CLINICAL_RAW["nct_id"],
                "title": "Title",
                "version": CLINICAL_RAW["version"],
            }
        )
        document.provenance["nct_id"] = CLINICAL_RAW["nct_id"]
        IRValidator().validate_document(document, raw=CLINICAL_RAW)
