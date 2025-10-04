from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

from Medical_KG.ingestion.ledger import IngestionLedger
from Medical_KG.ingestion.models import Document, IngestionResult
from Medical_KG.ingestion.utils import generate_doc_id
from Medical_KG.ingestion.events import PipelineEvent


@dataclass(slots=True)
class AdapterContext:
    ledger: IngestionLedger


RawPayloadT = TypeVar("RawPayloadT")


class BaseAdapter(Generic[RawPayloadT], ABC):
    source: str

    def __init__(self, context: AdapterContext) -> None:
        self.context = context
        self._emit_event: Callable[[PipelineEvent], None] | None = None

    async def iter_results(self, *args: object, **kwargs: object) -> AsyncIterator[IngestionResult]:
        """Yield ingestion results as they are produced."""

        keyword_args: dict[str, object] = dict(kwargs)
        resume = bool(keyword_args.pop("resume", False))
        fetcher = self.fetch(*args, **keyword_args)
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
                setattr(exc, "doc_id", doc_id)
                setattr(exc, "retry_count", getattr(exc, "retry_count", 0))
                setattr(exc, "is_retryable", getattr(exc, "is_retryable", False))
                self.context.ledger.record(
                    doc_id=doc_id,
                    state="auto_failed",
                    metadata={"error": str(exc)},
                )
                raise
            yield result

    async def run(self, *args: object, **kwargs: object) -> list[IngestionResult]:
        return [result async for result in self.iter_results(*args, **kwargs)]

    @abstractmethod
    def fetch(self, *args: Any, **kwargs: Any) -> AsyncIterator[RawPayloadT]:
        """Yield raw records from the upstream API."""

    @abstractmethod
    def parse(self, raw: RawPayloadT) -> Document:
        """Transform a raw record into a :class:`Document`."""

    def validate(self, document: Document) -> None:
        """Perform source-specific validations (override as needed)."""

    async def write(self, document: Document) -> IngestionResult:
        entry = self.context.ledger.record(
            doc_id=document.doc_id,
            state="auto_done",
            metadata={"source": document.source},
        )
        return IngestionResult(document=document, state=entry.state, timestamp=entry.timestamp)

    def build_doc_id(self, *, identifier: str, version: str, content: bytes) -> str:
        return generate_doc_id(self.source, identifier, version, content)

    def bind_event_emitter(self, emitter: Callable[[PipelineEvent], None] | None) -> None:
        """Register a callback used to forward custom adapter events."""

        self._emit_event = emitter

    def emit_event(self, event: PipelineEvent) -> None:
        if self._emit_event is None:
            return
        self._emit_event(event)
