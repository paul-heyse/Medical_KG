"""Data retention and purge pipeline."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, MutableMapping


@dataclass(slots=True)
class PurgePipeline:
    """Deletes documents across storage layers in correct order."""

    raw_store: MutableMapping[str, bytes]
    ir_store: MutableMapping[str, dict]
    chunk_store: MutableMapping[str, dict]
    embedding_store: MutableMapping[str, dict]
    kg_store: MutableMapping[str, dict]

    def purge(self, doc_id: str) -> None:
        self.raw_store.pop(doc_id, None)
        self.ir_store.pop(doc_id, None)
        self.chunk_store.pop(doc_id, None)
        self.embedding_store.pop(doc_id, None)
        self.kg_store.pop(doc_id, None)

    def exists_anywhere(self, doc_id: str) -> bool:
        return any(
            doc_id in store
            for store in (
                self.raw_store,
                self.ir_store,
                self.chunk_store,
                self.embedding_store,
                self.kg_store,
            )
        )


__all__ = ["PurgePipeline"]
