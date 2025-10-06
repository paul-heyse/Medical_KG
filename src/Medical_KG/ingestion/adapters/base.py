from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Collection
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Generic, Iterable, TypeVar, cast

from Medical_KG.ingestion.events import PipelineEvent
from Medical_KG.ingestion.ledger import IngestionLedger, LedgerState
from Medical_KG.ingestion.models import Document, IngestionResult
from Medical_KG.ingestion.utils import generate_doc_id


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
        completed_arg = keyword_args.pop("completed_ids", None)
        completed_lookup: set[str]
        if completed_arg is None:
            completed_lookup = set()
        elif isinstance(completed_arg, Collection) and not isinstance(completed_arg, (str, bytes)):
            completed_lookup = {str(identifier) for identifier in completed_arg}
        else:
            raise TypeError("completed_ids must be an iterable of document identifiers")
        keyword_args.pop("resume", None)
        fetcher = self.fetch(*args, **keyword_args)
        if not hasattr(fetcher, "__aiter__"):
            raise TypeError("fetch() must return an AsyncIterator")
        async for raw_record in fetcher:
            document: Document | None = None
            try:
                document = self.parse(raw_record)
                existing = self.context.ledger.get(document.doc_id)
                if existing is not None:
                    # Skip documents that are explicitly marked as completed
                    if completed_lookup and document.doc_id in completed_lookup:
                        continue
                    # Skip documents that are already completed (COMPLETED has no valid transitions)
                    if existing.state is LedgerState.COMPLETED:
                        continue
                    # Handle failed documents by transitioning through RETRYING
                    if existing.state is LedgerState.FAILED:
                        self.context.ledger.update_state(
                            doc_id=document.doc_id,
                            new_state=LedgerState.RETRYING,
                            metadata={"source": document.source},
                            adapter=self.source,
                        )
                        self.context.ledger.update_state(
                            doc_id=document.doc_id,
                            new_state=LedgerState.FETCHING,
                            metadata={"source": document.source},
                            adapter=self.source,
                        )
                    # Only transition to FETCHING if not already in a processing state
                    elif existing.state not in (
                        LedgerState.FETCHING,
                        LedgerState.FETCHED,
                        LedgerState.PARSING,
                        LedgerState.PARSED,
                        LedgerState.VALIDATING,
                        LedgerState.VALIDATED,
                        LedgerState.IR_BUILDING,
                        LedgerState.IR_READY,
                    ):
                        self.context.ledger.update_state(
                            doc_id=document.doc_id,
                            new_state=LedgerState.FETCHING,
                            metadata={"source": document.source},
                            adapter=self.source,
                        )
                else:
                    # New document, start with FETCHING
                    self.context.ledger.update_state(
                        doc_id=document.doc_id,
                        new_state=LedgerState.FETCHING,
                        metadata={"source": document.source},
                        adapter=self.source,
                    )
                self.validate(document)
                result = await self.write(document)
            except Exception as exc:  # pragma: no cover - surfaced to caller
                doc_id = document.doc_id if document else str(raw_record)
                setattr(exc, "doc_id", doc_id)
                setattr(exc, "retry_count", getattr(exc, "retry_count", 0))
                setattr(exc, "is_retryable", getattr(exc, "is_retryable", False))
                self.context.ledger.update_state(
                    doc_id=doc_id,
                    new_state=LedgerState.FAILED,
                    metadata={"error": str(exc)},
                    adapter=self.source,
                    error=exc,
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
        # Transition through proper states: FETCHING -> FETCHED -> PARSING -> PARSED -> VALIDATING -> VALIDATED -> IR_BUILDING -> IR_READY -> COMPLETED
        self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.FETCHED,
            metadata={"source": document.source},
            adapter=self.source,
        )
        self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.PARSING,
            metadata={"source": document.source},
            adapter=self.source,
        )
        self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.PARSED,
            metadata={"source": document.source},
            adapter=self.source,
        )
        self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.VALIDATING,
            metadata={"source": document.source},
            adapter=self.source,
        )
        self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.VALIDATED,
            metadata={"source": document.source},
            adapter=self.source,
        )
        self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.IR_BUILDING,
            metadata={"source": document.source},
            adapter=self.source,
        )
        self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.IR_READY,
            metadata={"source": document.source},
            adapter=self.source,
        )
        audit = self.context.ledger.update_state(
            doc_id=document.doc_id,
            new_state=LedgerState.COMPLETED,
            metadata={"source": document.source},
            adapter=self.source,
        )
        return IngestionResult(
            document=document,
            state=audit.new_state,
            timestamp=datetime.fromtimestamp(audit.timestamp, tz=timezone.utc),
            metadata=audit.metadata,
        )

    def build_doc_id(self, *, identifier: str, version: str, content: bytes) -> str:
        return generate_doc_id(self.source, identifier, version, content)

    def bind_event_emitter(self, emitter: Callable[[PipelineEvent], None] | None) -> None:
        """Register a callback used to forward custom adapter events."""

        self._emit_event = emitter

    def emit_event(self, event: PipelineEvent) -> None:
        if self._emit_event is None:
            return
        self._emit_event(event)
