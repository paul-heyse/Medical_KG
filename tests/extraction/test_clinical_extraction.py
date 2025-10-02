from Medical_KG.extraction import ClinicalExtractionService
from Medical_KG.extraction.service import Chunk
from Medical_KG.extraction.models import ExtractionType


def test_clinical_extraction_service_returns_expected_payload() -> None:
    text = (
        "Inclusion: age 18-65 years old patients were randomized. "
        "Results showed hazard ratio 0.72 (0.60-0.90, p=0.02). "
        "Grade 3 nausea occurred in 12/100 participants. "
        "Enalapril 10mg PO BID was administered."
    )
    chunk = Chunk(chunk_id="chunk-1", text=text)
    service = ClinicalExtractionService()

    envelope = service.extract_many([chunk])

    types = {extraction.type for extraction in envelope.payload}
    assert ExtractionType.PICO in types
    assert ExtractionType.EFFECT in types
    assert ExtractionType.ADVERSE_EVENT in types or ExtractionType.DOSE in types
