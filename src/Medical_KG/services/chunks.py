"""In-memory repository for document chunks used by the API layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable


@dataclass(slots=True)
class Chunk:
    chunk_id: str
    doc_id: str
    text: str
    section: str | None = None
    table_headers: list[str] = field(default_factory=list)


class ChunkRepository:
    """Very small in-memory repository for tests."""

    def __init__(self) -> None:
        self._chunks: dict[str, Chunk] = {}

    def add(self, chunk: Chunk) -> None:
        self._chunks[chunk.chunk_id] = chunk

    def get(self, chunk_id: str) -> Chunk | None:
        return self._chunks.get(chunk_id)

    def bulk_get(self, chunk_ids: Iterable[str]) -> list[Chunk]:
        return [self._chunks[chunk_id] for chunk_id in chunk_ids if chunk_id in self._chunks]

    def all(self) -> list[Chunk]:
        return list(self._chunks.values())
