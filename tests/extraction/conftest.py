"""Shared fixtures supporting extraction coverage tests."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

import pytest

from Medical_KG.extraction.models import (
    AdverseEventExtraction,
    DoseExtraction,
    EffectExtraction,
    EligibilityCriterion,
    EligibilityExtraction,
    EligibilityLogic,
    ExtractionEnvelope,
    ExtractionType,
    PICOExtraction,
)
from Medical_KG.extraction.service import Chunk
from Medical_KG.facets.models import Code, EvidenceSpan


@pytest.fixture
def clinical_snippets() -> dict[str, str]:
    """Representative snippets that trigger the built-in extractors."""

    return {
        "pico": "Patients receiving treatment versus placebo reported mortality reductions.",
        "effect": "Results showed hazard ratio 0.72 (0.60-0.90, p = 0.02) among 120/240 participants.",
        "ae": "Grade 3 nausea occurred in 12/100 participants and was considered serious.",
        "dose": "Metformin 500 mg PO BID was administered for twelve weeks.",
        "eligibility": "Inclusion criteria required age 18-65 years; exclusion criteria listed renal failure.",
    }


@pytest.fixture
def sample_chunk(clinical_snippets: dict[str, str]) -> Chunk:
    text = " ".join(clinical_snippets.values())
    return Chunk(chunk_id="chunk-001", text=text, doc_id="doc-123", section="Results")


@pytest.fixture
def evidence_span() -> EvidenceSpan:
    return EvidenceSpan(start=0, end=10, quote="placeholder")


@pytest.fixture
def effect_extraction(evidence_span: EvidenceSpan) -> EffectExtraction:
    return EffectExtraction(
        type=ExtractionType.EFFECT,
        name="hazard ratio",
        measure_type="HR",
        value=1.5,
        evidence_spans=[evidence_span],
    )


@pytest.fixture
def ae_extraction(evidence_span: EvidenceSpan) -> AdverseEventExtraction:
    return AdverseEventExtraction(
        type=ExtractionType.ADVERSE_EVENT,
        term="nausea",
        grade=3,
        count=12,
        denom=100,
        serious=False,
        codes=[Code(system="MedDRA", code="10028813", display="Nausea", confidence=0.4)],
        evidence_spans=[evidence_span],
    )


@pytest.fixture
def dose_extraction(evidence_span: EvidenceSpan) -> DoseExtraction:
    return DoseExtraction(
        type=ExtractionType.DOSE,
        amount=500.0,
        unit="mg",
        route="po",
        frequency_per_day=None,
        drug_codes=[],
        evidence_spans=[evidence_span],
    )


@pytest.fixture
def eligibility_extraction(evidence_span: EvidenceSpan) -> EligibilityExtraction:
    return EligibilityExtraction(
        type=ExtractionType.ELIGIBILITY,
        category="inclusion",
        criteria=[EligibilityCriterion(text="Age 18-65 years", logic=EligibilityLogic())],
        evidence_spans=[evidence_span],
    )


@pytest.fixture
def pico_extraction(evidence_span: EvidenceSpan) -> PICOExtraction:
    return PICOExtraction(
        type=ExtractionType.PICO,
        population="Adults",
        interventions=["metformin", "metformin"],
        comparators=["placebo", "placebo"],
        outcomes=["mortality", "mortality"],
        evidence_spans=[evidence_span],
    )


@pytest.fixture
def extraction_envelope(
    pico_extraction: PICOExtraction,
    effect_extraction: EffectExtraction,
    ae_extraction: AdverseEventExtraction,
    dose_extraction: DoseExtraction,
    eligibility_extraction: EligibilityExtraction,
) -> ExtractionEnvelope:
    payload = [
        pico_extraction,
        effect_extraction,
        ae_extraction,
        dose_extraction,
        eligibility_extraction,
    ]
    now = datetime.now(timezone.utc)
    return ExtractionEnvelope(
        model="qwen2",
        version="0.1.0",
        prompt_hash="prompt-hash",
        schema_hash="schema-hash",
        ts=now,
        extracted_at=now,
        chunk_ids=["chunk-001"],
        payload=payload,
    )


@pytest.fixture
def multi_chunk(sample_chunk: Chunk) -> Iterable[Chunk]:
    return [
        sample_chunk,
        Chunk(chunk_id="chunk-002", text=sample_chunk.text, doc_id="doc-123", section="Eligibility"),
    ]

