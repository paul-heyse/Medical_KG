from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from typing import Any

from Medical_KG.ingestion.ledger import IngestionLedger
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
        resume = bool(kwargs.pop("resume", False))
        results: list[IngestionResult] = []
        fetcher = self.fetch(*args, **kwargs)
        if not hasattr(fetcher, "__aiter__"):
            raise TypeError("fetch() must return an AsyncIterator")
        async for raw_record in fetcher:
            document: Document | None = None
            try:
                document = self.parse(raw_record)
                if resume:
                    existing = self.context.ledger.get(document.doc_id)
                    if existing is not None and existing.state == "auto_done":
                        continue
                self.context.ledger.record(
                    doc_id=document.doc_id,
                    state="auto_inflight",
                    metadata={"source": document.source},
                )
                self.validate(document)
                result = await self.write(document)
            except Exception as exc:  # pragma: no cover - surfaced to caller
                doc_id = document.doc_id if document else str(raw_record)
                self.context.ledger.record(
                    doc_id=doc_id,
                    state="auto_failed",
                    metadata={"error": str(exc)},
                )
                raise
            results.append(result)
        return results

    @abstractmethod
    async def fetch(self, *args: Any, **kwargs: Any) -> AsyncIterator[Any]:
        """Yield raw records from the upstream API."""

    @abstractmethod
    def parse(self, raw: Any) -> Document:
        """Transform a raw record into a :class:`Document`."""

    @abstractmethod
    def validate(self, document: Document) -> None:
        """Perform source-specific validations."""

    async def write(self, document: Document) -> IngestionResult:
        entry = self.context.ledger.record(
            doc_id=document.doc_id,
            state="auto_done",
            metadata={"source": document.source},
        )
        return IngestionResult(document=document, state=entry.state, timestamp=entry.timestamp)

    def build_doc_id(self, *, identifier: str, version: str, content: bytes) -> str:
        return generate_doc_id(self.source, identifier, version, content)
