import pytest

from Medical_KG.facets import FacetService
from Medical_KG.facets.models import FacetType
from Medical_KG.facets.service import Chunk


def test_generate_facets_detects_multiple_types() -> None:
    text = (
        "Patients receiving the treatment arm had a hazard ratio 0.68 (0.52-0.88, p=0.01) "
        "while Grade 3 nausea occurred in 12/100 participants taking Enalapril 10mg PO BID."
    )
    chunk = Chunk(chunk_id="chunk-1", doc_id="doc-1", text=text, section="results")
    service = FacetService()

    facets = service.generate_for_chunk(chunk)
    facet_types = {facet.type for facet in facets}

    assert FacetType.PICO in facet_types
    assert FacetType.ENDPOINT in facet_types
    assert FacetType.ADVERSE_EVENT in facet_types or FacetType.DOSE in facet_types


def test_index_payload_returns_codes() -> None:
    text = "Patients experienced Grade 2 nausea"
    chunk = Chunk(chunk_id="chunk-2", doc_id="doc-2", text=text, section="adverse_reactions")
    service = FacetService()

    service.generate_for_chunk(chunk)
    record = service.index_payload("chunk-2")

    assert record is not None
    assert record.chunk_id == "chunk-2"


def test_document_facets_deduplicate_by_doc() -> None:
    service = FacetService()
    text = "Grade 3 nausea occurred in 12/100 treatment arm patients."
    chunk_a = Chunk(chunk_id="c-1", doc_id="doc-7", text=text, section="adverse_reactions")
    chunk_b = Chunk(chunk_id="c-2", doc_id="doc-7", text=text, section="adverse_reactions")
    service.generate_for_chunk(chunk_a)
    service.generate_for_chunk(chunk_b)

    facets = service.document_facets("doc-7")
    ae_facets = [facet for facet in facets if facet.type == FacetType.ADVERSE_EVENT]

    assert len(ae_facets) == 1
    assert ae_facets[0].is_primary is True


def test_failed_generation_escalates_after_three_attempts() -> None:
    service = FacetService()
    failing_chunk = Chunk(
        chunk_id="fail-1",
        doc_id="doc-9",
        text="Hazard ratio 0 with impossible CI",
        section="results",
    )

    for _ in range(3):
        with pytest.raises(Exception):
            service.generate_for_chunk(failing_chunk)

    assert "fail-1" in service.escalation_queue
    reasons = service.failure_reasons("fail-1")
    assert reasons and any("Ratio effects" in reason for reason in reasons)
