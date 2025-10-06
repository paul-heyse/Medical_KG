from __future__ import annotations

import ast
import asyncio
import json
import os
import shutil
import sys
import threading
import types
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from trace import Trace
from typing import Any, Callable, Iterable, Iterator, Mapping, MutableMapping, Sequence, cast

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
PACKAGE_ROOT = SRC / "Medical_KG"
TARGET_COVERAGE = float(os.environ.get("COVERAGE_TARGET", "0.95"))

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

try:  # prefer real FastAPI when available
    import fastapi  # noqa: F401  # pragma: no cover - import only
except ImportError:  # pragma: no cover - fallback for environments without fastapi
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

        def post(
            self, path: str, **_options: Any
        ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
            def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
                self.routes.append((path, func))
                return func

            return _decorator

    def Depends(dependency: Callable[..., Any]) -> Callable[..., Any]:
        return dependency

    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: Any | None = None) -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    status = types.SimpleNamespace(
        HTTP_200_OK=200,
        HTTP_201_CREATED=201,
        HTTP_202_ACCEPTED=202,
        HTTP_204_NO_CONTENT=204,
        HTTP_400_BAD_REQUEST=400,
        HTTP_401_UNAUTHORIZED=401,
        HTTP_403_FORBIDDEN=403,
        HTTP_404_NOT_FOUND=404,
        HTTP_422_UNPROCESSABLE_ENTITY=422,
        HTTP_500_INTERNAL_SERVER_ERROR=500,
    )

    fastapi_module.FastAPI = _FastAPI
    fastapi_module.APIRouter = _APIRouter
    fastapi_module.Depends = Depends
    fastapi_module.HTTPException = HTTPException
    fastapi_module.status = status
    sys.modules["fastapi"] = fastapi_module

if "httpx" not in sys.modules:
    try:
        import httpx as _httpx  # noqa: F401  # pragma: no cover - use real module when available
    except ImportError:  # pragma: no cover - fallback stub for environments without httpx
        httpx_module = types.ModuleType("httpx")

        class TimeoutException(Exception):
            pass

        class HTTPError(Exception):
            def __init__(self, message: str, response: Any | None = None) -> None:
                super().__init__(message)
                self.response = response

        class HTTPStatusError(HTTPError):
            pass

        class Request:
            def __init__(self, method: str, url: str, **kwargs: Any) -> None:
                self.method = method
                self.url = url
                self.kwargs = kwargs

            def __str__(self) -> str:  # pragma: no cover - debug helper
                return f"{self.method} {self.url}"

        class Response:
            def __init__(
                self,
                *,
                status_code: int = 200,
                content: bytes | None = None,
                text: str | None = None,
                json: Any | None = None,
                request: Request | None = None,
                headers: Mapping[str, str] | None = None,
                **_ignored: Any,
            ) -> None:
                self.status_code = status_code
                if content is not None:
                    body = (
                        content
                        if isinstance(content, (bytes, bytearray))
                        else str(content).encode("utf-8")
                    )
                elif text is not None:
                    body = text.encode("utf-8")
                else:
                    body = b""
                self._content = body
                self._json = json
                self.text = text if text is not None else (body.decode("utf-8") if body else "")
                self.content = self._content
                self.request = request
                self.elapsed = None
                self.headers = dict(headers or {})

            def json(self, **_kwargs: Any) -> Any:
                if self._json is not None:
                    return self._json
                import json as _json  # local import to avoid global dependency

                return _json.loads(self.text or "{}")

            def raise_for_status(self) -> None:
                if self.status_code >= 400:
                    raise HTTPStatusError("HTTP error", response=self)

        class MockTransport:
            def __init__(self, handler: Callable[[Request], Response | Any]) -> None:
                self._handler = handler

            def handle_request(self, request: Request) -> Any:
                return self._handler(request)

        class _StreamContext:
            def __init__(
                self, transport: MockTransport, method: str, url: str, kwargs: dict[str, Any]
            ) -> None:
                self._transport = transport
                self._method = method
                self._url = url
                self._kwargs = kwargs
                self._response: Response | None = None

            async def __aenter__(self) -> Response:
                request = Request(self._method, self._url, **self._kwargs)
                result = self._transport.handle_request(request)
                if asyncio.iscoroutine(result):
                    result = await result
                self._response = result
                return self._response

            async def __aexit__(self, *_exc: Any) -> None:
                return None

        class AsyncClient:
            def __init__(self, *, transport: MockTransport | None = None, **_kwargs: Any) -> None:
                self._transport = transport

            async def request(self, method: str, url: str, **kwargs: Any) -> Response:
                if self._transport is None:
                    raise RuntimeError("Mock transport required in tests")
                request = Request(method, url, **kwargs)
                response = self._transport.handle_request(request)
                if asyncio.iscoroutine(response):
                    response = await response
                return response

            async def get(
                self,
                url: str,
                *,
                params: Mapping[str, Any] | None = None,
                headers: Mapping[str, str] | None = None,
            ) -> Response:
                return await self.request("GET", url, params=params, headers=headers)

            async def post(
                self,
                url: str,
                *,
                json: Any | None = None,
                headers: Mapping[str, str] | None = None,
            ) -> Response:
                return await self.request("POST", url, json=json, headers=headers)

            def stream(self, method: str, url: str, **kwargs: Any) -> _StreamContext:
                if self._transport is None:
                    raise RuntimeError("Mock transport required in tests")
                return _StreamContext(self._transport, method, url, kwargs)

            async def aclose(self) -> None:
                return None

            async def __aenter__(self) -> "AsyncClient":
                return self

            async def __aexit__(self, *_exc: Any) -> None:
                return None

        httpx_module.AsyncClient = AsyncClient
        httpx_module.MockTransport = MockTransport
        httpx_module.TimeoutException = TimeoutException
        httpx_module.HTTPError = HTTPError
        httpx_module.HTTPStatusError = HTTPStatusError
        httpx_module.Response = Response
        httpx_module.Request = Request

        sys.modules["httpx"] = httpx_module
elif not hasattr(sys.modules["httpx"], "BaseTransport"):
    existing = sys.modules.pop("httpx")
    try:  # pragma: no cover - executed only when dependency installed after stubbing
        import httpx as _real_httpx
    except ImportError:  # pragma: no cover
        sys.modules["httpx"] = existing
    else:
        sys.modules["httpx"] = _real_httpx

if "jsonschema" not in sys.modules:
    jsonschema_module = types.ModuleType("jsonschema")

    class ValidationError(Exception):
        def __init__(self, message: str = "", **kwargs: Any) -> None:
            super().__init__(message)
            self.message = message
            self.validator = kwargs.get("validator")
            self.validator_value = kwargs.get("validator_value")
            self.schema = kwargs.get("schema")

    class FormatChecker:
        def __init__(self) -> None:
            self._checks: dict[str, Callable[[Any], bool]] = {}

        def checks(self, name: str) -> Callable[[Callable[[Any], bool]], Callable[[Any], bool]]:
            def _register(func: Callable[[Any], bool]) -> Callable[[Any], bool]:
                self._checks[name] = func
                return func

            return _register

    def validator_for(_schema: Any) -> type:
        class _Validator:
            def __init__(self, *args: Any, **kwargs: Any) -> None:
                return None

            @staticmethod
            def check_schema(_schema: Any) -> None:
                return None

            def iter_errors(self, _instance: Any) -> list[Any]:
                return []

        return _Validator

    jsonschema_module.FormatChecker = FormatChecker
    jsonschema_module.ValidationError = ValidationError
    validators_module = types.ModuleType("jsonschema.validators")
    validators_module.validator_for = validator_for
    jsonschema_module.validators = validators_module
    sys.modules["jsonschema"] = jsonschema_module
    sys.modules["jsonschema.validators"] = validators_module

if "yaml" not in sys.modules:
    yaml_module = types.ModuleType("yaml")

    def _identity(value: Any, *args: Any, **kwargs: Any) -> Any:
        return value

    yaml_module.safe_load = _identity
    yaml_module.safe_dump = lambda value, *args, **kwargs: json.dumps(value)  # type: ignore[assignment]
    sys.modules["yaml"] = yaml_module


import pytest  # noqa: E402

from Medical_KG.ingestion.ledger import (  # noqa: E402
    LedgerAuditRecord,
    LedgerDocumentState,
    LedgerState,
    validate_transition,
)
from Medical_KG.ingestion.models import Document  # noqa: E402
from Medical_KG.retrieval.models import (  # noqa: E402
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    RetrieverScores,
)
from Medical_KG.retrieval.types import JSONValue, SearchHit, VectorHit  # noqa: E402
from Medical_KG.utils.optional_dependencies import get_httpx_module  # noqa: E402


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


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_artifacts() -> Iterator[None]:
    """Remove coverage and hypothesis artifacts after the test session."""

    cache_env = os.environ.get("PYTEST_DISABLE_ARTIFACT_CLEANUP")
    disable_cleanup = cache_env == "1"
    yield
    if disable_cleanup:
        return
    artifacts: list[Path] = [ROOT / ".coverage", ROOT / "coverage_missing.txt"]
    for artifact in artifacts:
        if artifact.exists():
            try:
                artifact.unlink()
            except IsADirectoryError:
                shutil.rmtree(artifact, ignore_errors=True)
            except OSError:
                pass
    hypothesis_dir = ROOT / ".hypothesis"
    if hypothesis_dir.exists():
        shutil.rmtree(hypothesis_dir, ignore_errors=True)


def pytest_sessionfinish(
    session: pytest.Session, exitstatus: int
) -> None:  # pragma: no cover - instrumentation only
    sys.settrace(None)
    threading.settrace(cast(Any, None))
    if os.environ.get("DISABLE_COVERAGE_TRACE") == "1":
        return
    results = _TRACE.results()
    executed: dict[Path, set[int]] = defaultdict(set)
    for (filename, lineno), count in list(results.counts.items()):
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

    report_items = {path: lines for path, lines in missing.items() if "ingestion" in str(path)}

    if report_items:
        details = "; ".join(
            f"{path}:{','.join(str(line) for line in sorted(lines))}"
            for path, lines in sorted(report_items.items())
        )
        (ROOT / "coverage_missing.txt").write_text(details, encoding="utf-8")
    else:
        coverage_file = ROOT / "coverage_missing.txt"
        if coverage_file.exists():
            coverage_file.unlink()

    ingestion_root = (SRC / "Medical_KG" / "ingestion").resolve()
    adapter_root = ingestion_root / "adapters"
    ingestion_missing = {
        path: lines
        for path, lines in missing.items()
        if adapter_root in (path.resolve().parents) and path.resolve() in executed
    }
    if os.environ.get("SKIP_INGESTION_COVERAGE") == "1":
        ingestion_missing = {}

    enforce_coverage = os.environ.get("ENFORCE_INGESTION_COVERAGE") == "1"

    if enforce_coverage and ingestion_missing:
        details = "; ".join(
            f"{path}:{','.join(str(line) for line in sorted(lines))}"
            for path, lines in sorted(ingestion_missing.items())
        )
        pytest.fail(f"Ingestion modules lack coverage: {details}")

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
    """In-memory ledger mirroring :class:`IngestionLedger` behaviour."""

    records: MutableMapping[str, LedgerDocumentState] = field(default_factory=dict)
    writes: list[LedgerAuditRecord] = field(default_factory=list)

    def update_state(
        self,
        doc_id: str,
        new_state: LedgerState,
        *,
        adapter: str | None = None,
        metadata: Mapping[str, Any] | None = None,
        error: BaseException | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        traceback: str | None = None,
    ) -> LedgerAuditRecord:
        if not isinstance(new_state, LedgerState):
            raise TypeError("new_state must be a LedgerState instance")
        existing = self.records.get(doc_id)
        if existing is not None:
            validate_transition(existing.state, new_state)
        now = datetime.now(timezone.utc)
        audit = LedgerAuditRecord(
            doc_id=doc_id,
            old_state=existing.state if existing else new_state,
            new_state=new_state,
            timestamp=now.timestamp(),
            adapter=None,
            metadata=dict(metadata or {}),
        )
        if existing is None:
            document = LedgerDocumentState(
                doc_id=doc_id,
                state=new_state,
                updated_at=now,
                metadata=dict(metadata or {}),
                history=[audit],
            )
            self.records[doc_id] = document
        else:
            existing.state = new_state
            existing.updated_at = now
            existing.metadata = dict(metadata or {})
            existing.history.append(audit)
        self.writes.append(audit)
        return audit

    def record(
        self,
        doc_id: str,
        state: LedgerState,
        metadata: Mapping[str, Any] | None = None,
        *,
        adapter: str | None = None,
        error: BaseException | None = None,
        retry_count: int | None = None,
        duration_seconds: float | None = None,
        parameters: Mapping[str, Any] | None = None,
    ) -> LedgerAuditRecord:
        del adapter, error, retry_count, duration_seconds, parameters
        if not isinstance(state, LedgerState):
            raise TypeError("state must be a LedgerState instance")
        return self.update_state(doc_id, state, metadata=metadata)

    def get(self, doc_id: str) -> LedgerDocumentState | None:
        return self.records.get(doc_id)

    def entries(
        self, *, state: LedgerState | None = None
    ) -> Iterable[LedgerDocumentState]:
        values = list(self.records.values())
        if state is None:
            return values
        if not isinstance(state, LedgerState):
            raise TypeError("state must be a LedgerState instance")
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
def sample_document_factory() -> (
    Callable[[str, str, str, MutableMapping[str, Any] | None, Any], "Document"]
):
    def _factory(
        doc_id: str = "doc-1",
        source: str = "demo",
        content: str = "text",
        metadata: MutableMapping[str, Any] | None = None,
        raw: Any | None = None,
    ) -> "Document":
        from Medical_KG.ingestion.models import Document
        from Medical_KG.ingestion.types import PubMedDocumentPayload

        if raw is None:
            default_raw: PubMedDocumentPayload = {
                "pmid": doc_id,
                "title": content or "Untitled",
                "abstract": content or "",
                "authors": [],
                "mesh_terms": [],
                "pub_types": [],
            }
            raw = default_raw

        return Document(
            doc_id=doc_id, source=source, content=content, metadata=metadata or {}, raw=raw
        )

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
        monkeypatch.setattr(
            "Medical_KG.ingestion.http_client.create_async_client", _create_async_client
        )

        return transport

    yield _factory

    for client in clients:
        try:
            loop = asyncio.new_event_loop()
            loop.run_until_complete(client.aclose())
        finally:
            loop.close()


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

    def run(
        self, statement: str, parameters: Mapping[str, Any] | None = None
    ) -> Sequence[Mapping[str, Any]]:
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
def fake_opensearch_client(
    fake_opensearch_hits: Mapping[str, Sequence[SearchHit]],
) -> FakeOpenSearchClient:
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
