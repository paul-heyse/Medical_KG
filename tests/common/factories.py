"""Typed factories for constructing common domain objects in tests."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, MutableMapping, Sequence

from Medical_KG.api.models import ErrorDetail, ErrorResponse, RetrieveResponse, RetrieveResult
from Medical_KG.chunking.document import Document as ChunkDocument, Section
from Medical_KG.ingestion.models import Document as IngestionDocument, IngestionResult
from Medical_KG.retrieval.models import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievalResult,
    RetrieverScores,
    RetrieverTiming,
)


def make_ingestion_document(
    *,
    doc_id: str = "doc-1",
    source: str = "test",
    content: str = "Example content",
    metadata: MutableMapping[str, Any] | None = None,
    raw: Any | None = None,
) -> IngestionDocument:
    """Return an ingestion document with safe defaults."""

    return IngestionDocument(
        doc_id=doc_id,
        source=source,
        content=content,
        metadata=metadata or {},
        raw=raw,
    )


def make_ingestion_result(
    *,
    document: IngestionDocument | None = None,
    state: str = "succeeded",
    timestamp: datetime | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> IngestionResult:
    """Create an :class:`IngestionResult` for adapter tests."""

    return IngestionResult(
        document=document or make_ingestion_document(),
        state=state,
        timestamp=timestamp or datetime.now(timezone.utc),
        metadata=metadata or {},
    )


def make_chunk_section(
    name: str = "Background",
    *,
    start: int = 0,
    end: int = 100,
    loinc_code: str | None = None,
) -> Section:
    """Construct a chunking section data structure."""

    return Section(name=name, start=start, end=end, loinc_code=loinc_code)


def make_chunk_document(
    *,
    doc_id: str = "doc-1",
    text: str = "Section text",
    sections: Iterable[Section] | None = None,
    source_system: str | None = "tests",
    media_type: str | None = "text/plain",
) -> ChunkDocument:
    """Return a semantic chunking document with optional sections."""

    return ChunkDocument(
        doc_id=doc_id,
        text=text,
        sections=list(sections) if sections is not None else [make_chunk_section()],
        tables=[],
        source_system=source_system,
        media_type=media_type,
    )


def make_retrieval_result(
    *,
    chunk_id: str = "chunk-1",
    doc_id: str = "doc-1",
    text: str = "Matched snippet",
    title_path: str | None = "Root/Section",
    section: str | None = "Section",
    score: float = 1.0,
    scores: RetrieverScores | None = None,
    start: int | None = None,
    end: int | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> RetrievalResult:
    """Produce a retrieval result with consistent score annotations."""

    return RetrievalResult(
        chunk_id=chunk_id,
        doc_id=doc_id,
        text=text,
        title_path=title_path,
        section=section,
        score=score,
        scores=scores or RetrieverScores(bm25=score),
        start=start,
        end=end,
        metadata=metadata or {},
    )


def make_retrieval_request(
    *,
    query: str = "test query",
    top_k: int = 5,
    from_: int = 0,
    filters: Mapping[str, Any] | None = None,
    intent: str | None = None,
    rerank_enabled: bool | None = None,
    explain: bool = False,
) -> RetrievalRequest:
    """Return a :class:`RetrievalRequest` with optional filters."""

    return RetrievalRequest(
        query=query,
        top_k=top_k,
        from_=from_,
        filters=filters or {},
        intent=intent,
        rerank_enabled=rerank_enabled,
        explain=explain,
    )


def make_retrieval_response(
    *,
    results: Sequence[RetrievalResult] | None = None,
    timings: Sequence[RetrieverTiming] | None = None,
    expanded_terms: Mapping[str, float] | None = None,
    intent: str = "test",
    latency_ms: float = 1.0,
    request: RetrievalRequest | None = None,
) -> RetrievalResponse:
    """Build a retrieval response for service doubles."""

    payload_results = list(results) if results is not None else [make_retrieval_result()]
    payload_timings = list(timings) if timings is not None else [RetrieverTiming(component="stub", duration_ms=latency_ms)]
    request = request or make_retrieval_request()
    return RetrievalResponse(
        results=payload_results,
        timings=payload_timings,
        expanded_terms=expanded_terms or {},
        intent=intent,
        latency_ms=latency_ms,
        from_=request.from_,
        size=len(payload_results),
        metadata={
            "from": request.from_,
            "top_k": request.top_k,
            "feature_flags": {"rerank_enabled": request.rerank_enabled if request.rerank_enabled is not None else True},
        },
    )


def make_retrieve_response_model(
    *,
    results: Sequence[RetrievalResult] | None = None,
    query_meta: Mapping[str, Any] | None = None,
) -> RetrieveResponse:
    """Create an API-layer RetrieveResponse model from retrieval results."""

    retrieve_results = [
        RetrieveResult(
            chunk_id=item.chunk_id,
            score=item.score,
            snippet=item.text,
            facet_types=list(item.metadata.get("facet_types", [])),
        )
        for item in (results or [make_retrieval_result()])
    ]
    return RetrieveResponse(results=retrieve_results, query_meta=dict(query_meta or {}))


def make_error_response_model(
    *,
    code: str = "invalid_request",
    message: str = "Request failed",
    details: Sequence[tuple[str, str]] | None = None,
    retriable: bool = False,
) -> ErrorResponse:
    """Return a typed error response for API tests."""

    payload = [ErrorDetail(field=field, message=detail) for field, detail in (details or [])]
    return ErrorResponse(code=code, message=message, details=payload, retriable=retriable)


__all__ = [
    "make_chunk_document",
    "make_chunk_section",
    "make_ingestion_document",
    "make_ingestion_result",
    "make_retrieval_request",
    "make_retrieval_response",
    "make_retrieval_result",
    "make_retrieve_response_model",
    "make_error_response_model",
]
