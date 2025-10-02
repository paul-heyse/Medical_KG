"""Facet orchestration service."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Iterable, Mapping

from pydantic import ValidationError

from Medical_KG.facets.generator import (
    GenerationRequest,
    FacetGenerationError,
    generate_facets,
    load_facets,
    serialize_facets,
)
from Medical_KG.facets.models import Facet, FacetIndexRecord, FacetModel, FacetType
from Medical_KG.facets.router import FacetRouter


@dataclass(slots=True)
class Chunk:
    """Minimal chunk representation used by the service."""

    chunk_id: str
    text: str
    section: str | None = None
    table_headers: list[str] = field(default_factory=list)


class FacetStorage:
    """In-memory storage for generated facets, used in tests and local dev."""

    def __init__(self) -> None:
        self._by_chunk: dict[str, list[str]] = {}
        self._meta: dict[str, dict[str, str]] = {}

    def set(self, chunk_id: str, facets: Iterable[Facet]) -> None:
        payloads = serialize_facets(list(facets))
        self._by_chunk[chunk_id] = payloads
        self._meta[chunk_id] = {
            "hash": hashlib.sha256("".join(payloads).encode()).hexdigest(),
        }

    def get(self, chunk_id: str) -> list[FacetModel]:
        payloads = self._by_chunk.get(chunk_id, [])
        if not payloads:
            return []
        return load_facets(payloads)

    def metadata(self, chunk_id: str) -> Mapping[str, str]:
        return self._meta.get(chunk_id, {})

    def index_record(self, chunk_id: str) -> FacetIndexRecord | None:
        facets = self.get(chunk_id)
        if not facets:
            return None
        return FacetIndexRecord(chunk_id=chunk_id, facets=facets)


class FacetService:
    """High-level API for facet generation and retrieval."""

    def __init__(self, storage: FacetStorage | None = None) -> None:
        self._storage = storage or FacetStorage()

    def generate_for_chunk(self, chunk: Chunk) -> list[FacetModel]:
        router = FacetRouter(table_headers=chunk.table_headers)
        facet_types = router.detect(chunk.text, section=chunk.section)
        request = GenerationRequest(chunk_id=chunk.chunk_id, text=chunk.text, section=chunk.section)
        try:
            facets = generate_facets(request, facet_types)
        except (ValidationError, FacetGenerationError) as exc:
            raise FacetGenerationError(str(exc)) from exc
        self._storage.set(chunk.chunk_id, facets)
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
