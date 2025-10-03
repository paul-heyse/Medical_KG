from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from typing import Any

from Medical_KG.ingestion.ledger import IngestionLedger, LedgerEntry
from Medical_KG.ingestion.models import Document, IngestionResult
from Medical_KG.ingestion.utils import generate_doc_id


@dataclass(slots=True)
class AdapterContext:
    ledger: IngestionLedger


class BaseAdapter(ABC):
    source: str

    def __init__(self, context: AdapterContext) -> None:
        self.context = context

    async def run(self, *args: Any, **kwargs: Any) -> Iterable[IngestionResult]:
        results: list[IngestionResult] = []
        async for raw_record in self.fetch(*args, **kwargs):
            document: Document | None = None
            try:
                document = self.parse(raw_record)
                if self._should_skip(document):
                    continue
                self.context.ledger.record(
                    doc_id=document.doc_id,
                    state="auto_inflight",
                    metadata=self._metadata(document),
                )
                self.validate(document)
                result = await self.write(document)
            except Exception as exc:  # pragma: no cover - surfaced to caller
                doc_id = document.doc_id if document else str(raw_record)
                self.context.ledger.record(
                    doc_id=doc_id,
                    state="auto_failed",
                    metadata=self._error_metadata(document, exc),
                )
                raise
            results.append(result)
        return results

    @abstractmethod
    async def fetch(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        """Yield raw records from the upstream API."""  # pragma: no cover - abstract contract

    @abstractmethod
    def parse(self, raw: Any) -> Document:
        """Transform a raw record into a :class:`Document`."""  # pragma: no cover - abstract contract

    @abstractmethod
    def validate(self, document: Document) -> None:
        """Perform source-specific validations."""  # pragma: no cover - abstract contract

    async def write(self, document: Document) -> IngestionResult:
        entry = self.context.ledger.record(
            doc_id=document.doc_id,
            state="auto_done",
            metadata=self._metadata(document),
        )
        return IngestionResult(document=document, state=entry.state, timestamp=entry.timestamp)

    def build_doc_id(self, *, identifier: str, version: str, content: bytes) -> str:
        return generate_doc_id(self.source, identifier, version, content)

    def _should_skip(self, document: Document) -> bool:
        existing: LedgerEntry | None = self.context.ledger.get(document.doc_id)
        return bool(existing and existing.state == "auto_done")

    @staticmethod
    def _metadata(document: Document) -> dict[str, Any]:
        return {
            "source": document.source,
            "document_metadata": dict(document.metadata),
        }

    @staticmethod
    def _error_metadata(document: Document | None, exc: Exception) -> dict[str, Any]:
        metadata: dict[str, Any] = {"error": str(exc)}
        if document is not None:
            metadata["source"] = document.source
            metadata["document_metadata"] = dict(document.metadata)
        return metadata
