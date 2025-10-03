import pytest

from Medical_KG.extraction import (
    ClinicalExtractionService,
    ExtractionEvaluator,
    ExtractionValidator,
    PromptLibrary,
    build_kg_statements,
)
from Medical_KG.extraction.models import EffectExtraction, EvidenceSpan, ExtractionType
from Medical_KG.extraction.service import Chunk


def test_prompt_library_includes_global_rules() -> None:
    library = PromptLibrary()
    prompt = library.build(ExtractionType.PICO, text="Adults received metformin.")
    assert "Return valid JSON" in prompt.system


def test_validator_dead_letter_on_invalid_effect() -> None:
    validator = ExtractionValidator()
    extraction = EffectExtraction(
        type=ExtractionType.EFFECT,
        name="hazard ratio",
        measure_type="HR",
        value=0.0,
        evidence_spans=[EvidenceSpan(start=0, end=5, quote="HR 0")],
    )
    with pytest.raises(Exception):
        validator.validate(extraction, text="HR 0", facet_mode=False)
    assert validator.dead_letter.records


def test_clinical_extraction_service_returns_expected_payload() -> None:
    text = (
        "Inclusion: age 18-65 years old patients were randomized. "
        "Results showed hazard ratio 0.72 (0.60-0.90, p=0.02). "
        "Grade 3 nausea occurred in 12/100 participants. "
        "Enalapril 10mg PO BID was administered."
    )
    chunk = Chunk(chunk_id="chunk-1", text=text, doc_id="doc-1", section="results")
    service = ClinicalExtractionService()

    envelope = service.extract_many([chunk])

    types = {extraction.type for extraction in envelope.payload}
    assert ExtractionType.PICO in types
    assert ExtractionType.EFFECT in types
    assert ExtractionType.ADVERSE_EVENT in types or ExtractionType.DOSE in types

    statements = list(build_kg_statements(envelope, document_uri="doc-1"))
    assert statements

    evaluator = ExtractionEvaluator()
    metrics = evaluator.evaluate(envelope.payload, envelope.payload)
    assert metrics.pico_completeness >= 0
