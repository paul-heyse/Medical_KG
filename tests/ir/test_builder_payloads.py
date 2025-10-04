"""Integration tests for ``IrBuilder`` payload handling."""

from Medical_KG.ingestion.types import (
    ClinicalDocumentPayload,
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
    IRValidator().validate_document(document, raw=raw)


def test_ir_builder_without_payload() -> None:
    builder = IrBuilder()
    document = builder.build(
        doc_id="doc:1",
        source="generic",
        uri="https://example.org/doc/1",
        text="Plain text content",
    )
    assert document.text == "Plain text content"
    IRValidator().validate_document(document)


def test_ir_builder_smoke_uses_typed_payload_text() -> None:
    builder = IrBuilder()
    raw: PubMedDocumentPayload = {
        "pmid": "99999",
        "title": "Typed Title",
        "abstract": "Typed abstract body.",
        "authors": ["Author"],
        "mesh_terms": ["Term"],
        "pub_types": ["Journal Article"],
        "pmcid": "PMC99999",
        "doi": "10.1000/typed",
        "journal": "Typed Journal",
        "pub_year": "2024",
        "pubdate": "2024-05-01",
    }
    document = builder.build(
        doc_id="pubmed:99999",
        source="pubmed",
        uri="https://pubmed.ncbi.nlm.nih.gov/99999/",
        text="Placeholder text should be replaced",
        raw=raw,
    )
    assert document.text.startswith("Typed Title")
    assert "Typed abstract body." in document.text
    assert document.provenance["pubmed"]["pmid"] == "99999"
    IRValidator().validate_document(document, raw=raw)
