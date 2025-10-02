from Medical_KG.facets import FacetService
from Medical_KG.facets.models import FacetType
from Medical_KG.facets.service import Chunk


def test_generate_facets_detects_multiple_types() -> None:
    text = (
        "Patients receiving the treatment arm had a hazard ratio 0.68 (0.52-0.88, p=0.01) "
        "while Grade 3 nausea occurred in 12/100 participants taking Enalapril 10mg PO BID."
    )
    chunk = Chunk(chunk_id="chunk-1", text=text, section="results")
    service = FacetService()

    facets = service.generate_for_chunk(chunk)
    facet_types = {facet.type for facet in facets}

    assert FacetType.PICO in facet_types
    assert FacetType.ENDPOINT in facet_types
    assert FacetType.ADVERSE_EVENT in facet_types or FacetType.DOSE in facet_types


def test_index_payload_returns_codes() -> None:
    text = "Patients experienced Grade 2 nausea"
    chunk = Chunk(chunk_id="chunk-2", text=text, section="adverse_reactions")
    service = FacetService()

    service.generate_for_chunk(chunk)
    record = service.index_payload("chunk-2")

    assert record is not None
    assert record.chunk_id == "chunk-2"
