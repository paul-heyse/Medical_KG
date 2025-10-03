from __future__ import annotations

import json
from typing import Sequence

import pytest

from Medical_KG.chunking import (
    ChunkGraphWriter,
    ChunkIndexer,
    ChunkingPipeline,
    ChunkSearchIndexer,
    Document,
    FacetGenerator,
    Section,
    Table,
)
from Medical_KG.embeddings import EmbeddingService, QwenEmbeddingClient, SPLADEExpander


def build_document() -> Document:
    text = (
        "## Introduction Patients with diabetes mellitus often require glucose monitoring. "
        "## Methods Participants received metformin 500 mg twice daily. "
        "Table 1: Laboratory results [glucose 7.2 mmol/L]. "
        "## Results The hazard ratio was 0.76 with 95% CI 0.61-0.95 with no significant difference observed."
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
            digest="",
            start=table_start,
            end=table_end,
        )
    ]
    return Document(
        doc_id="DOC123",
        text=text,
        sections=sections,
        tables=tables,
        source_system="pmc",
        media_type="text",
    )


@pytest.fixture()
def embedding_service() -> EmbeddingService:
    return EmbeddingService(
        qwen=QwenEmbeddingClient(dimension=12, batch_size=8),
        splade=SPLADEExpander(top_k=6, batch_size=4),
    )


def test_chunking_pipeline_generates_chunks_and_metrics(
    embedding_service: EmbeddingService,
) -> None:
    document = build_document()
    pipeline = ChunkingPipeline(
        facet_generator=FacetGenerator(), embedding_service=embedding_service
    )
    result = pipeline.run(document)
    assert result.chunks
    assert result.metrics.intra_coherence > 0
    assert result.metrics.inter_coherence >= 0
    if len(result.chunks) > 10:
        assert result.metrics.below_min_tokens <= int(len(result.chunks) * 0.1)
    assert result.index_documents
    assert any(doc.title_path for doc in result.index_documents if doc.granularity == "chunk")
    table_chunk = next(chunk for chunk in result.chunks if chunk.table_html is not None)
    assert "glucose" in table_chunk.table_digest
    assert table_chunk.table_lines and any("glucose" in line for line in table_chunk.table_lines)
    endpoint_chunk = next(chunk for chunk in result.chunks if chunk.facet_type == "endpoint")
    assert endpoint_chunk.facet_json["metric"].lower() == "hazard ratio"
    assert endpoint_chunk.facet_embedding_qwen is not None
    assert endpoint_chunk.facet_json["negated"] is True
    assert all(chunk.embedding_qwen for chunk in result.chunks)
    assert all(chunk.created_at.tzinfo is not None for chunk in result.chunks)
    assert any(chunk.title_path for chunk in result.chunks if chunk.section)
    overlaps = [chunk for chunk in result.chunks if chunk.overlap_with_prev]
    if overlaps:
        assert {"chunk_id", "start", "end", "token_window"} <= overlaps[0].overlap_with_prev.keys()


def test_chunk_ids_are_stable(embedding_service: EmbeddingService) -> None:
    document = build_document()
    pipeline = ChunkingPipeline(embedding_service=embedding_service)
    first = pipeline.run(document).chunks
    second = pipeline.run(document).chunks
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]


def test_chunk_indexer_produces_multi_granularity(embedding_service: EmbeddingService) -> None:
    document = build_document()
    pipeline = ChunkingPipeline(embedding_service=embedding_service)
    chunks = pipeline.run(document).chunks
    indexer = ChunkIndexer()
    docs = indexer.build_documents(chunks)
    granularities = {doc.granularity for doc in docs}
    assert {"chunk", "paragraph", "section"}.issubset(granularities)
    merges = indexer.neighbor_merge(chunks, min_cosine=0.0)
    assert merges


def test_neighbor_merge_avoids_low_similarity(embedding_service: EmbeddingService) -> None:
    document = build_document()
    pipeline = ChunkingPipeline(embedding_service=embedding_service)
    chunks = pipeline.run(document).chunks
    indexer = ChunkIndexer()
    merges = indexer.neighbor_merge(chunks, min_cosine=0.95)
    assert not merges  # strict threshold prevents merges


def test_guardrails_keep_list_items_together(embedding_service: EmbeddingService) -> None:
    doc = Document(
        doc_id="DOC999",
        text="- Primary endpoint was HR 0.8; - Secondary endpoint was OR 1.1.",
        sections=[Section(name="results", start=0, end=70)],
    )
    pipeline = ChunkingPipeline(embedding_service=embedding_service)
    chunks = pipeline.run(doc).chunks
    assert len(chunks) == 1
    assert "Primary endpoint" in chunks[0].text


def test_facet_json_serialises_negation() -> None:
    document = build_document()
    pipeline = ChunkingPipeline()
    chunk = next(chunk for chunk in pipeline.run(document).chunks if chunk.facet_type == "endpoint")
    serialised = json.dumps(chunk.facet_json)
    assert "metric" in serialised


class FakeChunkSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object] | None]] = []

    def run(self, query: str, parameters: dict[str, object] | None = None) -> None:
        self.calls.append((query, parameters))


class FakeChunkIndices:
    def __init__(self) -> None:
        self.created: list[dict[str, object]] = []
        self.reloads = 0
        self._exists = False

    def exists(self, index: str) -> bool:
        return self._exists

    def create(self, index: str, body: dict[str, object]) -> None:
        self._exists = True
        self.created.append({"index": index, "body": body})

    def reload_search_analyzers(self, index: str) -> None:
        self.reloads += 1


class FakeChunkClient:
    def __init__(self) -> None:
        self.indices = FakeChunkIndices()
        self.bulk_operations: list[list[dict[str, object]]] = []

    def bulk(self, operations: Sequence[dict[str, object]]) -> dict[str, object]:
        self.bulk_operations.append(list(operations))
        return {"errors": False}


def test_chunk_graph_writer_syncs_embeddings(embedding_service: EmbeddingService) -> None:
    document = build_document()
    pipeline = ChunkingPipeline(embedding_service=embedding_service)
    result = pipeline.run(document)
    chunks = result.chunks
    session = FakeChunkSession()
    writer = ChunkGraphWriter(session)
    writer.sync(document.doc_id, chunks, neighbor_merges=result.neighbor_merges)
    queries = [query for query, _ in session.calls]
    assert any("MERGE (c:Chunk" in query for query in queries)
    assert any("CALL db.index.vector.createNodeIndex" in query for query in queries)
    assert any("OVERLAPS" in query for query in queries)
    assert any("SIMILAR_TO" in query for query in queries)
    has_chunk = next(
        params for query, params in session.calls if query.strip().startswith("MERGE (d:Document")
    )
    assert isinstance(has_chunk["index"], int)


def test_chunk_search_indexer_indexes_multi_granularity(
    embedding_service: EmbeddingService,
) -> None:
    document = build_document()
    pipeline = ChunkingPipeline(embedding_service=embedding_service)
    result = pipeline.run(document)
    client = FakeChunkClient()
    indexer = ChunkSearchIndexer(client)
    indexer.ensure_index()
    indexer.index_chunks(result.chunks, result.index_documents)
    assert client.indices.created
    assert client.bulk_operations
    payloads = client.bulk_operations[0][1::2]
    assert any(payload.get("title_path") for payload in payloads)
    assert any("table_lines" in payload for payload in payloads)


def test_chunk_search_indexer_build_query_uses_boosts() -> None:
    client = FakeChunkClient()
    indexer = ChunkSearchIndexer(client)
    query = indexer.build_query("glucose")
    fields = query["query"]["bool"]["should"][0]["multi_match"]["fields"]
    assert set(fields) == {"title_path^2.0", "facet_json^1.6", "table_lines^1.2", "body^1.0"}
