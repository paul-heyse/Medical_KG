"""Facet orchestration service."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field

from Medical_KG.facets.dedup import deduplicate_facets
from Medical_KG.facets.generator import (
    FacetGenerationError,
    GenerationRequest,
    generate_facets,
    load_facets,
    serialize_facets,
)
from Medical_KG.facets.models import FacetIndexRecord, FacetModel
from Medical_KG.facets.router import FacetRouter
from Medical_KG.facets.validator import FacetValidationError, FacetValidator
from pydantic import ValidationError


@dataclass(slots=True)
class Chunk:
    """Minimal chunk representation used by the service."""

    chunk_id: str
    doc_id: str
    text: str
    section: str | None = None
    table_headers: list[str] = field(default_factory=list)


class FacetStorage:
    """In-memory storage for generated facets, used in tests and local dev."""

    def __init__(self) -> None:
        self._by_chunk: dict[str, list[str]] = {}
        self._chunk_doc: dict[str, str] = {}
        self._doc_chunks: dict[str, set[str]] = defaultdict(set)
        self._doc_cache: dict[str, list[str]] = {}
        self._meta: dict[str, dict[str, str]] = {}

    def set(self, chunk_id: str, doc_id: str, facets: Iterable[FacetModel]) -> None:
        payloads = serialize_facets(list(facets))
        self._by_chunk[chunk_id] = payloads
        self._chunk_doc[chunk_id] = doc_id
        self._doc_chunks[doc_id].add(chunk_id)
        self._meta[chunk_id] = {
            "hash": hashlib.sha256("".join(payloads).encode()).hexdigest(),
        }
        self._refresh_doc_cache(doc_id)

    def _refresh_doc_cache(self, doc_id: str) -> None:
        payloads: list[str] = []
        for chunk_id in self._doc_chunks.get(doc_id, set()):
            payloads.extend(self._by_chunk.get(chunk_id, []))
        if not payloads:
            self._doc_cache.pop(doc_id, None)
            return
        models = load_facets(payloads)
        deduped = deduplicate_facets(models)
        self._doc_cache[doc_id] = [facet.model_dump_json(by_alias=True) for facet in deduped]

    def get(self, chunk_id: str) -> list[FacetModel]:
        payloads = self._by_chunk.get(chunk_id, [])
        if not payloads:
            return []
        return load_facets(payloads)

    def get_document_facets(self, doc_id: str) -> list[FacetModel]:
        payloads = self._doc_cache.get(doc_id, [])
        if not payloads:
            return []
        return load_facets(payloads)

    def metadata(self, chunk_id: str) -> Mapping[str, str]:
        return self._meta.get(chunk_id, {})

    def index_record(self, chunk_id: str) -> FacetIndexRecord | None:
        doc_id = self._chunk_doc.get(chunk_id)
        if not doc_id:
            return None
        facets = self.get_document_facets(doc_id)
        if not facets:
            return None
        return FacetIndexRecord(chunk_id=chunk_id, facets=facets)


class FacetService:
    """High-level API for facet generation and retrieval."""

    def __init__(self, storage: FacetStorage | None = None) -> None:
        self._storage = storage or FacetStorage()
        self._validator = FacetValidator()
        self._failure_counts: dict[str, int] = defaultdict(int)
        self._failure_reasons: dict[str, list[str]] = defaultdict(list)
        self._manual_review: set[str] = set()

    def generate_for_chunk(self, chunk: Chunk) -> list[FacetModel]:
        router = FacetRouter(table_headers=chunk.table_headers)
        facet_types = router.detect(chunk.text, section=chunk.section)
        request = GenerationRequest(chunk_id=chunk.chunk_id, text=chunk.text, section=chunk.section)
        try:
            facets = generate_facets(request, facet_types)
            validated = [self._validator.validate(facet, text=chunk.text) for facet in facets]
        except (ValidationError, FacetGenerationError, FacetValidationError) as exc:
            self._record_failure(chunk.chunk_id, reason=str(exc))
            raise FacetGenerationError(str(exc)) from exc
        else:
            self._clear_failure(chunk.chunk_id)
        self._storage.set(chunk.chunk_id, chunk.doc_id, validated)
        return self._storage.get(chunk.chunk_id)

    def generate_for_chunks(self, chunks: Iterable[Chunk]) -> dict[str, list[FacetModel]]:
        results: dict[str, list[FacetModel]] = {}
        for chunk in chunks:
            results[chunk.chunk_id] = self.generate_for_chunk(chunk)
        return results

    def get_facets(self, chunk_id: str) -> list[FacetModel]:
        return self._storage.get(chunk_id)

    def index_payload(self, chunk_id: str) -> FacetIndexRecord | None:
        return self._storage.index_record(chunk_id)

    def document_facets(self, doc_id: str) -> list[FacetModel]:
        return self._storage.get_document_facets(doc_id)

    def metadata(self, chunk_id: str) -> Mapping[str, str]:
        return self._storage.metadata(chunk_id)

    @property
    def escalation_queue(self) -> list[str]:
        return sorted(self._manual_review)

    def failure_reasons(self, chunk_id: str) -> list[str]:
        return list(self._failure_reasons.get(chunk_id, []))

    def _record_failure(self, chunk_id: str, *, reason: str) -> None:
        self._failure_counts[chunk_id] += 1
        self._failure_reasons[chunk_id].append(reason)
        if self._failure_counts[chunk_id] >= 3:
            self._manual_review.add(chunk_id)

    def _clear_failure(self, chunk_id: str) -> None:
        if chunk_id in self._failure_counts:
            del self._failure_counts[chunk_id]
        self._failure_reasons.pop(chunk_id, None)
        self._manual_review.discard(chunk_id)
