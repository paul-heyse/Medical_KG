from __future__ import annotations

from Medical_KG.chunking import (
    ChunkingPipeline,
    Document,
    FacetGenerator,
    Section,
    Table,
)


def build_document() -> Document:
    text = (
        "## Introduction Patients with diabetes mellitus often require glucose monitoring. "
        "## Methods Participants received metformin 500 mg twice daily. "
        "Table 1: Laboratory results [glucose 7.2 mmol/L]. "
        "## Results The hazard ratio was 0.76 with 95% CI 0.61-0.95."
    )
    intro_end = text.index("## Methods")
    methods_end = text.index("Table 1")
    results_start = text.index("## Results")
    sections = [
        Section(name="introduction", start=0, end=intro_end),
        Section(name="methods", start=intro_end, end=methods_end),
        Section(name="results", start=results_start, end=len(text)),
    ]
    table_start = text.index("Table 1")
    table_end = table_start + len("Table 1: Laboratory results [glucose 7.2 mmol/L]. ")
    tables = [
        Table(
            html="<table><tr><td>glucose</td><td>7.2 mmol/L</td></tr></table>",
            digest="glucose:7.2 mmol/L",
            start=table_start,
            end=table_end,
        )
    ]
    return Document(doc_id="DOC123", text=text, sections=sections, tables=tables, source_system="pmc", media_type="text")


def test_chunking_pipeline_generates_chunks_and_metrics() -> None:
    document = build_document()
    pipeline = ChunkingPipeline(facet_generator=FacetGenerator())
    result = pipeline.run(document)
    assert result.chunks
    assert result.metrics.intra_coherence > 0
    chunk_ids = {chunk.chunk_id for chunk in result.chunks}
    assert len(chunk_ids) == len(result.chunks)
    table_chunk = next(chunk for chunk in result.chunks if chunk.table_html is not None)
    assert "glucose" in table_chunk.table_digest
    endpoint_chunk = next(chunk for chunk in result.chunks if chunk.facet_type == "endpoint")
    assert endpoint_chunk.facet_json["metric"].lower() == "hazard ratio"
    dose_chunk = next(chunk for chunk in result.chunks if chunk.intent.value == "dose")
    assert dose_chunk.facet_type == "dose"


def test_chunk_ids_are_stable() -> None:
    document = build_document()
    pipeline = ChunkingPipeline()
    first = pipeline.run(document).chunks
    second = pipeline.run(document).chunks
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
