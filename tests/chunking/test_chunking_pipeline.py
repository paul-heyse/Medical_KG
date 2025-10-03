from __future__ import annotations

from typing import Iterable, List

from Medical_KG.chunking.chunker import SemanticChunker, Sentence, _sentence_split
from Medical_KG.chunking.document import Document, Section, Table
from Medical_KG.chunking.pipeline import ChunkingPipeline, FacetVectorRecord
from Medical_KG.chunking.profiles import get_profile
from Medical_KG.chunking.tagger import ClinicalIntent


class FixedEmbeddingService:
    def __init__(self) -> None:
        self.calls: list[tuple[tuple[str, ...], tuple[str, ...] | None]] = []

    def embed_texts(
        self, texts: Iterable[str], *, sparse_texts: Iterable[str] | None = None
    ) -> tuple[List[List[float]], List[dict[str, float]]]:
        texts = tuple(texts)
        sparse = tuple(sparse_texts) if sparse_texts is not None else None
        self.calls.append((texts, sparse))
        dense = [[1.0, 0.0] for _ in texts]
        sparse_vectors = [{"term": 1.0} for _ in texts]
        return dense, sparse_vectors


def build_document() -> Document:
    table_html = "<table><tr><td>Group</td><td>Rate</td></tr><tr><td>A</td><td>60%</td></tr></table>"
    text = (
        "INTRODUCTION\n"
        "Study overview sentence.\n"
        "1. First item.\n"
        "2. Second item.\n"
        "METHODS\n"
        "Participants received 10 mg dose daily.\n"
        "RESULTS\n"
        "The hazard ratio was 0.45 (95% CI 0.30-0.60).\n"
        f"{table_html}\n"
        "DISCUSSION\n"
        "Recommendations were positive.\n"
    )
    intro_end = text.index("METHODS")
    methods_end = text.index("RESULTS")
    results_end = text.index("DISCUSSION")
    table_start = text.index(table_html)
    table_end = table_start + len(table_html)
    sections = [
        Section(name="introduction", start=0, end=intro_end),
        Section(name="methods", start=intro_end, end=methods_end),
        Section(name="results", start=methods_end, end=results_end),
        Section(name="discussion", start=results_end, end=len(text)),
    ]
    tables = [Table(html=table_html, digest="table digest", start=table_start, end=table_end)]
    return Document(doc_id="DOC42", text=text, sections=sections, tables=tables)


def test_sentence_split_and_guardrails() -> None:
    spans = _sentence_split("Sentence one. Sentence two? Final!")
    assert [span[0] for span in spans] == ["Sentence one.", "Sentence two?", "Final!"]

    chunker = SemanticChunker(profile=get_profile("guideline"))
    previous = Sentence(text="1. First item", start=0, end=14, section=None)
    current = Sentence(text="2. Second item", start=15, end=30, section=None)

    assert chunker._should_delay_boundary(previous, current)  # type: ignore[attr-defined]


def test_chunking_pipeline_outputs_embeddings_and_facets() -> None:
    document = build_document()
    embedding_service = FixedEmbeddingService()
    pipeline = ChunkingPipeline(embedding_service=embedding_service, embed_facets=True)

    result = pipeline.run(document)

    assert result.chunks, "Expected at least one chunk"
    assert all(chunk.chunk_id.startswith("DOC42") for chunk in result.chunks)
    assert any(chunk.table_lines for chunk in result.chunks)
    assert result.index_documents and {doc.granularity for doc in result.index_documents} == {
        "chunk",
        "paragraph",
        "section",
    }
    assert result.neighbor_merges, "Expected neighbor merges when embeddings are present"
    assert any(isinstance(record, FacetVectorRecord) for record in result.facet_vectors)
    assert embedding_service.calls

    assert any("1." in chunk.text and "2." in chunk.text for chunk in result.chunks)
    assert any(chunk.intent == ClinicalIntent.ENDPOINT for chunk in result.chunks)
