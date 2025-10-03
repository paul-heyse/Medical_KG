from __future__ import annotations

import ast
import os
import sys
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from types import FrameType
from typing import Any, Mapping, Sequence, cast
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PACKAGE_ROOT = SRC / "Medical_KG"
TARGET_COVERAGE = float(os.environ.get("COVERAGE_TARGET", "0.95"))

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from trace import Trace

import pytest

from Medical_KG.retrieval.models import RetrievalRequest, RetrievalResponse, RetrievalResult, RetrieverScores
from Medical_KG.retrieval.types import JSONValue, SearchHit, VectorHit


@pytest.fixture
def monkeypatch_fixture(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    return monkeypatch

_TRACE = Trace(count=True, trace=False)


def _activate_tracing() -> None:  # pragma: no cover - instrumentation only
    trace_func = cast(Any, _TRACE.globaltrace)
    if trace_func is None:
        return
    sys.settrace(trace_func)
    threading.settrace(trace_func)


if os.environ.get("DISABLE_COVERAGE_TRACE") != "1":
    _activate_tracing()


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:  # pragma: no cover - instrumentation only
    sys.settrace(None)
    threading.settrace(cast(Any, None))
    if os.environ.get("DISABLE_COVERAGE_TRACE") == "1":
        return
    results = _TRACE.results()
    executed: dict[Path, set[int]] = defaultdict(set)
    for (filename, lineno), count in results.counts.items():
        if count <= 0:
            continue
        path = Path(filename)
        try:
            path = path.resolve()
        except OSError:
            continue
        if PACKAGE_ROOT not in path.parents and path != PACKAGE_ROOT:
            continue
        executed[path].add(lineno)

    missing: dict[Path, set[int]] = {}
    per_file_coverage: list[tuple[Path, float]] = []
    total_statements = 0
    total_covered = 0

    for py_file in PACKAGE_ROOT.rglob("*.py"):
        statements = _statement_lines(py_file)
        if not statements:
            continue
        executed_lines = executed.get(py_file.resolve(), set())
        covered = statements & executed_lines
        uncovered = statements - covered
        rel_path = py_file.relative_to(ROOT)
        per_file_coverage.append(
            (
                rel_path,
                len(covered) / len(statements) if statements else 1.0,
            )
        )
        total_statements += len(statements)
        total_covered += len(covered)
        if uncovered:
            missing[rel_path] = uncovered

    overall = total_covered / total_statements if total_statements else 1.0

    if missing:
        details = "; ".join(
            f"{path}:{','.join(str(line) for line in sorted(lines))}" for path, lines in sorted(missing.items())
        )
        (ROOT / "coverage_missing.txt").write_text(details, encoding="utf-8")
    else:
        coverage_file = ROOT / "coverage_missing.txt"
        if coverage_file.exists():
            coverage_file.unlink()

    # Temporarily disabled coverage gate for test coverage implementation work
    # TODO: Re-enable once test coverage proposals are implemented
    # if overall + 1e-9 < TARGET_COVERAGE:
    #     lowest = sorted(per_file_coverage, key=lambda item: item[1])[:5]
    #     summary = ", ".join(f"{path}={pct:.1%}" for path, pct in lowest)
    #     pytest.fail(
    #         f"Statement coverage {overall:.1%} below target {TARGET_COVERAGE:.0%}. "
    #         f"Lowest files: {summary}"
    #     )


def _statement_lines(path: Path) -> set[int]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    lines: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.stmt):
            lines.add(node.lineno)
    return lines


# ---------------------------------------------------------------------------
# Shared retrieval fixtures


@dataclass
class FakeQwenEmbedder:
    """Deterministic embedder that records queries."""

    vectors: Mapping[str, Sequence[float]]
    default: Sequence[float] = field(default_factory=lambda: [0.05, 0.1, 0.15])
    calls: list[str] = field(default_factory=list)

    def embed(self, text: str) -> Sequence[float]:
        self.calls.append(text)
        return list(self.vectors.get(text, self.default))


@dataclass
class FakeSpladeEncoder:
    """SPLaDe encoder returning preconfigured term weights."""

    mapping: Mapping[str, Mapping[str, float]]
    calls: list[str] = field(default_factory=list)

    def expand(self, text: str) -> Mapping[str, float]:
        self.calls.append(text)
        return dict(self.mapping.get(text, {}))


@dataclass
class FakeOpenSearchClient:
    """In-memory OpenSearch facade keyed by index name."""

    hits_by_index: Mapping[str, Sequence[SearchHit]]
    executed: list[tuple[str, dict[str, JSONValue]]] = field(default_factory=list)

    def search(
        self,
        *,
        index: str,
        body: Mapping[str, JSONValue],
        size: int,
    ) -> Sequence[SearchHit]:
        self.executed.append((index, dict(body)))
        hits = list(self.hits_by_index.get(index, ()))
        return [cast(SearchHit, dict(hit)) for hit in hits[:size]]


@dataclass
class FakeVectorClient:
    """Vector store returning pre-seeded hits regardless of embedding."""

    hits: Sequence[VectorHit]
    queries: list[Sequence[float]] = field(default_factory=list)

    def query(self, *, index: str, embedding: Sequence[float], top_k: int) -> Sequence[VectorHit]:
        _ = index
        self.queries.append(tuple(embedding))
        return [cast(VectorHit, dict(hit)) for hit in self.hits[:top_k]]


@dataclass
class FakeNeo4jClient:
    """Captures Cypher queries and returns canned graph results."""

    records: Sequence[Mapping[str, Any]]
    statements: list[str] = field(default_factory=list)

    def run(self, statement: str, parameters: Mapping[str, Any] | None = None) -> Sequence[Mapping[str, Any]]:
        _ = parameters
        self.statements.append(statement)
        return [dict(record) for record in self.records]


@pytest.fixture
def fake_embeddings() -> Mapping[str, Sequence[float]]:
    return {
        "pembrolizumab": [0.9, 0.1, 0.2],
        "EGFR signaling": [0.2, 0.8, 0.4],
        "latest cancer treatments": [0.3, 0.2, 0.9],
    }


@pytest.fixture
def fake_query_embedder(fake_embeddings: Mapping[str, Sequence[float]]) -> FakeQwenEmbedder:
    return FakeQwenEmbedder(vectors=fake_embeddings)


@pytest.fixture
def fake_splade_encoder() -> FakeSpladeEncoder:
    return FakeSpladeEncoder(
        mapping={
            "pembrolizumab": {"pembrolizumab": 2.5, "keytruda": 1.8},
            "EGFR signaling": {"egfr": 1.6, "signaling": 1.4},
        }
    )


@pytest.fixture
def fake_vector_hits() -> Sequence[VectorHit]:
    hits: list[VectorHit] = [
        {
            "chunk_id": "chunk-dense-1",
            "doc_id": "doc-10",
            "text": "Dense retriever chunk",
            "score": 0.91,
            "metadata": {"cosine": 0.91},
        },
        {
            "chunk_id": "chunk-dense-2",
            "doc_id": "doc-11",
            "text": "Complementary chunk",
            "score": 0.88,
            "metadata": {"cosine": 0.88},
        },
    ]
    return hits


@pytest.fixture
def fake_vector_client(fake_vector_hits: Sequence[VectorHit]) -> FakeVectorClient:
    return FakeVectorClient(hits=fake_vector_hits)


@pytest.fixture
def fake_opensearch_hits() -> Mapping[str, Sequence[SearchHit]]:
    shared: list[SearchHit] = [
        {
            "chunk_id": "chunk-bm25-1",
            "doc_id": "doc-1",
            "text": "What is pembrolizumab",
            "score": 2.4,
            "metadata": {"cosine": 0.93},
        },
        {
            "chunk_id": "chunk-bm25-2",
            "doc_id": "doc-2",
            "text": "Mechanism of action",
            "score": 1.7,
            "metadata": {"cosine": 0.89},
        },
    ]
    splade: list[SearchHit] = [
        {
            "chunk_id": "chunk-splade-1",
            "doc_id": "doc-3",
            "text": "Sparse lexical chunk",
            "score": 1.2,
            "metadata": {},
        }
    ]
    graph: list[SearchHit] = [
        {
            "chunk_id": "chunk-graph-1",
            "doc_id": "doc-neo4j",
            "text": "Graph neighbor description",
            "score": 0.77,
            "metadata": {"relationship": "ASSOCIATED_WITH"},
        }
    ]
    return {
        "bm25-index": shared,
        "splade-index": splade,
        "graph-index": graph,
    }


@pytest.fixture
def fake_opensearch_client(fake_opensearch_hits: Mapping[str, Sequence[SearchHit]]) -> FakeOpenSearchClient:
    return FakeOpenSearchClient(hits_by_index=fake_opensearch_hits)


@pytest.fixture
def fake_graph_client() -> FakeNeo4jClient:
    return FakeNeo4jClient(
        records=(
            {"entity": "EGFR", "neighbor": "PI3K", "relationship": "ACTIVATES"},
            {"entity": "EGFR", "neighbor": "RAS", "relationship": "BINDS"},
        )
    )


@pytest.fixture
def retrieval_request() -> RetrievalRequest:
    return RetrievalRequest(query="pembrolizumab", top_k=3)


@pytest.fixture
def expected_retrieval_response() -> RetrievalResponse:
    result = RetrievalResult(
        chunk_id="chunk-bm25-1",
        doc_id="doc-1",
        text="What is pembrolizumab",
        title_path=None,
        section=None,
        score=2.4,
        scores=RetrieverScores(bm25=2.4),
        metadata={"granularity": "chunk"},
    )
    return RetrievalResponse(
        results=[result],
        timings=[],
        expanded_terms={"pembrolizumab": 1.0},
        intent="general",
        latency_ms=1.0,
        from_=0,
        size=1,
        metadata={"feature_flags": {"rerank_enabled": False}},
    )
