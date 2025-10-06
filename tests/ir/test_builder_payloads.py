"""Integration tests for ``IrBuilder`` payload handling."""

import pytest

from Medical_KG.ingestion.types import (
    ClinicalDocumentPayload,
    MeshDocumentPayload,
    NiceGuidelineDocumentPayload,
    OpenPrescribingDocumentPayload,
    PmcDocumentPayload,
    PubMedDocumentPayload,
)
from Medical_KG.ir.builder import IrBuilder
from Medical_KG.ir.validator import IRValidator


def test_ir_builder_uses_pubmed_payload() -> None:
    builder = IrBuilder()
    raw: PubMedDocumentPayload = {
        "pmid": "12345",
        "title": "Example Title",
        "abstract": "Summary of the article.",
        "authors": ["Author One", "Author Two"],
        "mesh_terms": ["Term1", "Term2"],
        "pub_types": ["Journal Article"],
        "pmcid": "PMC12345",
        "doi": "10.1000/example",
        "journal": "Example Journal",
        "pub_year": "2024",
        "pubdate": "2024-01-01",
    }
    document = builder.build(
        doc_id="pubmed:12345",
        source="pubmed",
        uri="https://pubmed.ncbi.nlm.nih.gov/12345/",
        text="",
        raw=raw,
    )
    sections = [block.section for block in document.blocks]
    assert sections[0] == "title"
    assert "abstract" in sections
    assert document.provenance["pubmed"]["pmid"] == "12345"
    assert document.provenance["mesh_terms"] == ["Term1", "Term2"]
    assert document.metadata["payload_family"] == "literature"
    assert document.metadata["identifier"] == "12345"
    assert document.metadata["doi"] == "10.1000/example"
    validator = IRValidator()
    validator.validate_document(document, raw=raw)


def test_ir_builder_extracts_pmc_sections() -> None:
    builder = IrBuilder()
    raw: PmcDocumentPayload = {
        "pmcid": "PMC67890",
        "title": "PMC Article",
        "abstract": "PMC abstract text.",
        "sections": [
            {"title": "Introduction", "text": "Intro text."},
            {"title": "Methods", "text": "Methods text."},
        ],
        "tables": [],
        "figures": [],
        "references": [],
    }
    document = builder.build(
        doc_id="pmc:67890",
        source="pmc",
        uri="https://www.ncbi.nlm.nih.gov/pmc/articles/PMC67890/",
        text="",
        raw=raw,
    )
    heading_sections = [block for block in document.blocks if block.type == "heading"]
    paragraph_sections = [
        block
        for block in document.blocks
        if block.type == "paragraph" and block.section not in {"abstract"}
    ]
    assert heading_sections, "Expected heading blocks from PMC sections"
    assert len(paragraph_sections) >= 2
    assert document.provenance["pmcid"] == "PMC67890"
    assert document.metadata["payload_type"] == "pmc"
    assert document.metadata["identifier"] == "PMC67890"
    IRValidator().validate_document(document, raw=raw)


def test_ir_builder_extracts_clinical_payload() -> None:
    builder = IrBuilder()
    raw: ClinicalDocumentPayload = {
        "nct_id": "NCT00000000",
        "title": "Clinical Study",
        "version": "v1",
        "arms": [
            {"armType": "Experimental", "description": "Treatment arm."},
            {"armType": "Placebo", "description": "Control arm."},
        ],
        "eligibility": "Adults over 18",
        "status": "Recruiting",
        "phase": "Phase 2",
        "study_type": "Interventional",
        "lead_sponsor": "Example Sponsor",
        "enrollment": 100,
        "start_date": "2024-01-01",
        "completion_date": "2025-01-01",
        "outcomes": [
            {"measure": "Survival", "description": "Overall survival", "timeFrame": "12 months"},
        ],
    }
    document = builder.build(
        doc_id="nct:NCT00000000",
        source="clinicaltrials",
        uri="https://clinicaltrials.gov/study/NCT00000000",
        text="",
        raw=raw,
    )
    arm_blocks = [block for block in document.blocks if block.section == "arm"]
    outcome_blocks = [block for block in document.blocks if block.section == "outcome"]
    assert len(arm_blocks) == 2
    assert len(outcome_blocks) == 1
    assert document.provenance["nct_id"] == "NCT00000000"
    assert document.metadata["payload_family"] == "clinical"
    assert document.metadata["version"] == "v1"
    IRValidator().validate_document(document, raw=raw)


def test_ir_builder_without_payload() -> None:
    builder = IrBuilder()
    with pytest.raises(ValueError, match="raw"):
        builder.build(
            doc_id="doc:1",
            source="generic",
            uri="https://example.org/doc/1",
            text="Plain text content",
            raw=None,
        )


def test_ir_builder_extracts_guideline_metadata() -> None:
    builder = IrBuilder()
    raw: NiceGuidelineDocumentPayload = {
        "uid": "NG123",
        "title": "Guideline Title",
        "summary": "Summary paragraph",
        "url": "https://nice.org.uk/NG123",
        "licence": "OpenGov",
    }
    document = builder.build(
        doc_id="nice:NG123",
        source="nice",
        uri="https://nice.org.uk/NG123",
        text="",
        raw=raw,
    )
    assert document.metadata["payload_family"] == "guideline"
    assert document.metadata["identifier"] == "NG123"
    assert document.metadata["summary"] == "Summary paragraph"
    IRValidator().validate_document(document, raw=raw)


def test_ir_builder_extracts_terminology_metadata() -> None:
    builder = IrBuilder()
    raw: MeshDocumentPayload = {
        "name": "Aspirin",
        "terms": ["Acetylsalicylic Acid"],
        "descriptor_id": "D001241",
    }
    document = builder.build(
        doc_id="mesh:D001241",
        source="mesh",
        uri="https://meshb.nlm.nih.gov/record/ui?ui=D001241",
        text="",
        raw=raw,
    )
    assert document.metadata["payload_family"] == "terminology"
    assert document.metadata["identifier"] == "D001241"
    assert document.metadata["title"] == "Aspirin"
    IRValidator().validate_document(document, raw=raw)


def test_ir_builder_extracts_openprescribing_metadata() -> None:
    builder = IrBuilder()
    raw: OpenPrescribingDocumentPayload = {
        "identifier": "chemoprevention",
        "record": {"title": "Chemoprevention stats"},
    }
    document = builder.build(
        doc_id="openprescribing:chemoprevention",
        source="openprescribing",
        uri="https://openprescribing.net/chemoprevention",
        text="",
        raw=raw,
    )
    assert document.metadata["payload_family"] == "knowledge_base"
    assert document.metadata["identifier"] == "chemoprevention"
    IRValidator().validate_document(document, raw=raw)
