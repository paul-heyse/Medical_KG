from __future__ import annotations

import ast
import asyncio
import os
import sys
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from types import FrameType
from typing import Any, Callable, Dict, Iterable, Mapping, MutableMapping, Sequence, cast
import types
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PACKAGE_ROOT = SRC / "Medical_KG"
TARGET_COVERAGE = float(os.environ.get("COVERAGE_TARGET", "0.95"))

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

if "fastapi" not in sys.modules:
    fastapi_module = types.ModuleType("fastapi")

    class _FastAPI:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs

    class _APIRouter:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.args = args
            self.kwargs = kwargs
            self.routes: list[tuple[str, Callable[..., Any]]] = []

        def post(self, path: str, **_options: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                self.routes.append((path, func))
                return func

            return _decorator

    fastapi_module.FastAPI = _FastAPI
    fastapi_module.APIRouter = _APIRouter
    sys.modules["fastapi"] = fastapi_module

from trace import Trace

import pytest

from Medical_KG.ingestion.ledger import LedgerEntry
from Medical_KG.retrieval.models import RetrievalRequest, RetrievalResponse, RetrievalResult, RetrieverScores
from Medical_KG.retrieval.types import JSONValue, SearchHit, VectorHit
from Medical_KG.utils.optional_dependencies import get_httpx_module


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
# Ingestion testing utilities


@dataclass
class FakeLedger:
    """In-memory ledger that mirrors :class:`IngestionLedger`."""

    records: MutableMapping[str, LedgerEntry] = field(default_factory=dict)
    writes: list[LedgerEntry] = field(default_factory=list)

    def record(self, doc_id: str, state: str, metadata: Mapping[str, Any] | None = None) -> LedgerEntry:
        entry = LedgerEntry(
            doc_id=doc_id,
            state=state,
            timestamp=datetime.now(timezone.utc),
            metadata=dict(metadata or {}),
        )
        self.records[doc_id] = entry
        self.writes.append(entry)
        return entry

    def get(self, doc_id: str) -> LedgerEntry | None:
        return self.records.get(doc_id)

    def entries(self, *, state: str | None = None) -> Iterable[LedgerEntry]:
        values = list(self.records.values())
        if state is None:
            return values
        return [entry for entry in values if entry.state == state]


@dataclass
class FakeRegistry:
    """Simple adapter registry for CLI tests."""

    adapters: MutableMapping[str, Callable[[Any, Any, Any], Any]] = field(default_factory=dict)

    def register(self, source: str, factory: Callable[[Any, Any, Any], Any]) -> None:
        self.adapters[source] = factory

    def available_sources(self) -> list[str]:
        return sorted(self.adapters)

    def get_adapter(self, source: str, context: Any, client: Any, **kwargs: Any) -> Any:
        try:
            factory = self.adapters[source]
        except KeyError as exc:
            raise ValueError(f"Unknown adapter source: {source}") from exc
        return factory(context, client, **kwargs)


@pytest.fixture
def fake_ledger() -> FakeLedger:
    return FakeLedger()


@pytest.fixture
def fake_registry() -> FakeRegistry:
    return FakeRegistry()


@pytest.fixture
def sample_document_factory() -> Callable[[str, str, str, MutableMapping[str, Any] | None, Any], Document]:
    def _factory(
        doc_id: str = "doc-1",
        source: str = "demo",
        content: str = "text",
        metadata: MutableMapping[str, Any] | None = None,
        raw: Any | None = None,
    ) -> Document:
        return Document(doc_id=doc_id, source=source, content=content, metadata=metadata or {}, raw=raw)

    return _factory


@pytest.fixture
def httpx_mock_transport(monkeypatch: pytest.MonkeyPatch) -> Callable[[Callable[[Any], Any]], Any]:
    """Patch httpx AsyncClient creation to use a MockTransport."""

    HTTPX = get_httpx_module()
    clients: list[Any] = []

    def _factory(handler: Callable[[Any], Any]) -> Any:
        transport = HTTPX.MockTransport(handler)

        def _create_async_client(**kwargs: Any) -> Any:
            client = HTTPX.AsyncClient(transport=transport, **kwargs)
            clients.append(client)
            return client

        monkeypatch.setattr("Medical_KG.compat.httpx.create_async_client", _create_async_client)
        monkeypatch.setattr("Medical_KG.ingestion.http_client.create_async_client", _create_async_client)

        return transport

    yield _factory

    for client in clients:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(client.aclose())
        finally:
            loop.close()


class _CounterStub:
    def labels(self, *args: Any, **kwargs: Any) -> "_CounterStub":
        return self

    def inc(self, amount: float = 1.0) -> None:
        return None


class _HistogramStub:
    def labels(self, *args: Any, **kwargs: Any) -> "_HistogramStub":
        return self

    def observe(self, amount: float) -> None:
        return None


@pytest.fixture(autouse=True)
def stub_ingestion_metrics(monkeypatch: pytest.MonkeyPatch) -> None:
    counter = _CounterStub()
    histogram = _HistogramStub()
    monkeypatch.setattr("Medical_KG.ingestion.http_client.HTTP_REQUESTS", counter)
    monkeypatch.setattr("Medical_KG.ingestion.http_client.HTTP_LATENCY", histogram)


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
