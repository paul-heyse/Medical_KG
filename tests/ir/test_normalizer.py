from pathlib import Path

import pytest

from Medical_KG.ingestion.types import ClinicalDocumentPayload
from Medical_KG.ir.builder import ClinicalTrialsBuilder
from Medical_KG.ir.models import Block
from Medical_KG.ir.normalizer import TextNormalizer
from Medical_KG.ir.storage import IrStorage
from Medical_KG.ir.validator import IRValidator, ValidationError

CLINICAL_RAW: ClinicalDocumentPayload = {
    "nct_id": "NCT-TRIAL-1",
    "title": "Trial Title",
    "version": "v1",
    "arms": [],
    "eligibility": "Adults with sepsis",
    "outcomes": [],
}


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
    path = storage.write(document)
    assert path.exists()


def test_validator_rejects_bad_offsets() -> None:
    builder = ClinicalTrialsBuilder()
    study = {"title": "Title", "status": "Active", "eligibility": "Patients"}
    document = builder.build_from_study(doc_id="study#2", uri="uri", study=study)
    document.provenance["nct_id"] = CLINICAL_RAW["nct_id"]
    document.metadata.update(
        {
            "payload_family": "clinical",
            "payload_type": "clinical_document",
            "identifier": CLINICAL_RAW["nct_id"],
            "title": "Title",
            "version": CLINICAL_RAW["version"],
        }
    )
    document.blocks[0].start = 10
    with pytest.raises(ValidationError):
        IRValidator().validate_document(document, raw=CLINICAL_RAW)
