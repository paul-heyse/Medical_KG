import pytest

from Medical_KG.retrieval.models import RetrievalResult, RetrieverScores
from Medical_KG.retrieval.neighbor import NeighborMerger, filter_by_relationship


def _result(chunk: str, doc: str, text: str, cosine: float, score: float) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk,
        doc_id=doc,
        text=text,
        title_path=None,
        section=None,
        score=score,
        scores=RetrieverScores(dense=score),
        metadata={"cosine": cosine},
    )


def test_neighbor_merger_combines_high_similarity() -> None:
    merger = NeighborMerger(min_cosine=0.85, max_tokens=200)
    first = _result("c1", "doc1", "Intro", 0.9, 0.8)
    second = _result("c2", "doc1", "Details", 0.88, 0.7)
    merged = merger.merge([first, second])
    assert len(merged) == 1
    assert "Details" in merged[0].text
    assert merged[0].score == pytest.approx(0.8)


def test_neighbor_merger_respects_token_budget() -> None:
    merger = NeighborMerger(min_cosine=0.85, max_tokens=5)
    first = _result("c1", "doc1", "ABCDE", 0.9, 0.8)
    second = _result("c2", "doc1", "FGHIJ", 0.9, 0.7)
    merged = merger.merge([first, second])
    assert len(merged) == 2


def test_neighbor_merger_requires_same_document() -> None:
    merger = NeighborMerger(min_cosine=0.5, max_tokens=200)
    first = _result("c1", "doc1", "Intro", 0.9, 0.8)
    second = _result("c2", "doc2", "Details", 0.9, 0.7)
    merged = merger.merge([first, second])
    assert len(merged) == 2


def test_neighbor_merger_combines_multiple_neighbors() -> None:
    merger = NeighborMerger(min_cosine=0.85, max_tokens=500)
    first = _result("c1", "doc1", "Intro", 0.9, 0.9)
    second = _result("c2", "doc1", "Middle", 0.88, 0.85)
    third = _result("c3", "doc1", "Conclusion", 0.87, 0.8)
    merged = merger.merge([first, second, third])
    assert len(merged) == 1
    assert merged[0].text.count("\n") == 2


def test_filter_by_relationship() -> None:
    results = [
        _result("c1", "doc1", "Intro", 0.9, 0.9),
        RetrievalResult(
            chunk_id="c2",
            doc_id="doc1",
            text="Graph edge",
            title_path=None,
            section=None,
            score=0.8,
            scores=RetrieverScores(bm25=0.8),
            metadata={"relationship": "ASSOCIATED_WITH"},
        ),
        RetrievalResult(
            chunk_id="c3",
            doc_id="doc1",
            text="Filtered edge",
            title_path=None,
            section=None,
            score=0.7,
            scores=RetrieverScores(bm25=0.7),
            metadata={"relationship": "UNRELATED"},
        ),
    ]
    filtered = filter_by_relationship(results, {"ASSOCIATED_WITH"})
    assert len(filtered) == 2
    assert all(item.metadata.get("relationship") != "UNRELATED" for item in filtered)
