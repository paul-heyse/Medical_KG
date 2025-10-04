from __future__ import annotations

import asyncio
import contextlib
import logging
import time
import traceback
from collections.abc import AsyncIterator, Iterable, Sequence
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Protocol

from Medical_KG.ingestion import registry as ingestion_registry
from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.events import (
    AdapterStateChange,
    BatchProgress,
    DocumentCompleted,
    DocumentFailed,
    DocumentStarted,
    EventFilter,
    EventTransformer,
    PipelineEvent,
    PipelineResult,
    build_pipeline_id,
    event_to_dict,
)
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.ledger import IngestionLedger
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.telemetry import HttpTelemetry
from Medical_KG.utils.optional_dependencies import (
    CounterProtocol,
    GaugeProtocol,
    HistogramProtocol,
    build_counter,
    build_gauge,
    build_histogram,
)


class AdapterRegistry(Protocol):
    def get_adapter(
        self,
        source: str,
        context: AdapterContext,
        client: AsyncHttpClient,
        **kwargs: Any,
    ) -> BaseAdapter[Any]: ...

    def available_sources(self) -> list[str]: ...


_DEFAULT_BUFFER_SIZE = 100
_DEFAULT_PROGRESS_INTERVAL = 100
_DEFAULT_CHECKPOINT_INTERVAL = 1000
LOGGER = logging.getLogger(__name__)

PIPELINE_EVENT_COUNTER: CounterProtocol = build_counter(
    "ingest_pipeline_events_total",
    "Number of ingestion pipeline events emitted",
    ("event_type", "adapter"),
)
PIPELINE_DURATION_SECONDS: HistogramProtocol = build_histogram(
    "ingest_pipeline_duration_seconds",
    "Duration of ingestion pipeline executions",
    (0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0, 600.0),
)
PIPELINE_QUEUE_DEPTH: GaugeProtocol = build_gauge(
    "ingest_pipeline_queue_depth",
    "Depth of the ingestion pipeline event queue",
    ("adapter",),
)
PIPELINE_CHECKPOINT_LATENCY: HistogramProtocol = build_histogram(
    "ingest_pipeline_checkpoint_latency_seconds",
    "Latency between checkpoint progress events",
    (0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
)

PIPELINE_CONSUMPTION_COUNTER: CounterProtocol = build_counter(
    "ingest_pipeline_consumption_total",
    "Number of ingestion pipeline consumptions by mode",
    ("mode", "adapter"),
)


class IngestionPipeline:
    """Coordinate adapters, ledger interactions, and retry semantics."""

    def __init__(
        self,
        ledger: IngestionLedger,
        *,
        registry: AdapterRegistry | None = None,
        client_factory: type[AsyncHttpClient] | None = None,
        client_telemetry: (
            HttpTelemetry
            | Sequence[HttpTelemetry]
            | Mapping[str, HttpTelemetry | Sequence[HttpTelemetry]]
        )
        | None = None,
        enable_client_metrics: bool | None = None,
    ) -> None:
        self.ledger = ledger
        self._registry = registry or ingestion_registry
        self._client_factory = client_factory or AsyncHttpClient
        self._client_kwargs: dict[str, Any] = {}
        if client_telemetry is not None:
            self._client_kwargs["telemetry"] = client_telemetry
        if enable_client_metrics is not None:
            self._client_kwargs["enable_metrics"] = enable_client_metrics

    def run(
        self,
        source: str,
        params: Iterable[dict[str, Any]] | None = None,
        *,
        resume: bool = False,
    ) -> list[PipelineResult]:
        """Execute an adapter synchronously."""

        return asyncio.run(
            self._collect_results(
                source,
                params=params,
                resume=resume,
                buffer_size=_DEFAULT_BUFFER_SIZE,
                progress_interval=_DEFAULT_PROGRESS_INTERVAL,
                checkpoint_interval=_DEFAULT_CHECKPOINT_INTERVAL,
                event_filter=None,
                event_transformer=None,
                completed_ids=None,
                total_estimated=None,
                consumption_mode="run_async",
            )
        )

    async def run_async(
        self,
        source: str,
        *,
        params: Iterable[dict[str, Any]] | None = None,
        resume: bool = False,
        buffer_size: int = _DEFAULT_BUFFER_SIZE,
        progress_interval: int = _DEFAULT_PROGRESS_INTERVAL,
        checkpoint_interval: int = _DEFAULT_CHECKPOINT_INTERVAL,
        event_filter: EventFilter | None = None,
        event_transformer: EventTransformer | None = None,
        completed_ids: Iterable[str] | None = None,
        total_estimated: int | None = None,
    ) -> list[PipelineResult]:
        """Execute an adapter within an existing asyncio event loop.

        This helper materialises the full result set in memory and should only
        be used for small batches. Prefer :meth:`stream_events` for
        observability-friendly, backpressured consumption of pipeline activity.
        """

        return await self._collect_results(
            source,
            params=params,
            resume=resume,
            buffer_size=buffer_size,
            progress_interval=progress_interval,
            checkpoint_interval=checkpoint_interval,
            event_filter=event_filter,
            event_transformer=event_transformer,
            completed_ids=completed_ids,
            total_estimated=total_estimated,
            consumption_mode="run_async",
        )

    def status(self) -> dict[str, list[dict[str, Any]]]:
        summary: dict[str, list[dict[str, Any]]] = {}
        for entry in self.ledger.entries():
            summary.setdefault(entry.state.value, []).append(
                {"doc_id": entry.doc_id, "metadata": dict(entry.metadata)}
            )
        return summary

    def iter_results(
        self,
        source: str,
        *,
        params: Iterable[dict[str, Any]] | None = None,
        resume: bool = False,
        buffer_size: int = _DEFAULT_BUFFER_SIZE,
        progress_interval: int = _DEFAULT_PROGRESS_INTERVAL,
        checkpoint_interval: int = _DEFAULT_CHECKPOINT_INTERVAL,
        event_filter: EventFilter | None = None,
        event_transformer: EventTransformer | None = None,
        completed_ids: Iterable[str] | None = None,
        total_estimated: int | None = None,
    ) -> AsyncIterator[Document]:
        """Stream :class:`Document` instances as they are produced.

        This method remains for backwards compatibility and filters the richer
        event stream down to successful documents. New integrations should
        consume :meth:`stream_events` directly to access progress and error
        events.
        """

        async def _generator() -> AsyncIterator[Document]:
            async for event in self.stream_events(
                source,
                params=params,
                resume=resume,
                buffer_size=buffer_size,
                progress_interval=progress_interval,
                checkpoint_interval=checkpoint_interval,
                event_filter=event_filter,
                event_transformer=event_transformer,
                completed_ids=completed_ids,
                total_estimated=total_estimated,
            ):
                if isinstance(event, DocumentCompleted):
                    yield event.document

        return _generator()

    async def _collect_results(
        self,
        source: str,
        *,
        params: Iterable[dict[str, Any]] | None,
        resume: bool,
        buffer_size: int,
        progress_interval: int,
        checkpoint_interval: int,
        event_filter: EventFilter | None,
        event_transformer: EventTransformer | None,
        completed_ids: Iterable[str] | None,
        total_estimated: int | None,
        consumption_mode: str,
    ) -> list[PipelineResult]:
        invocations = self._normalise_params(params)
        results: list[PipelineResult] = []
        for invocation in invocations:
            documents: list[Document] = []
            failures: list[DocumentFailed] = []
            started_at_dt = self._utcnow()
            stream = self.stream_events(
                source,
                params=None if invocation is None else [invocation],
                resume=resume,
                buffer_size=buffer_size,
                progress_interval=progress_interval,
                checkpoint_interval=checkpoint_interval,
                event_filter=event_filter,
                event_transformer=event_transformer,
                completed_ids=completed_ids,
                total_estimated=total_estimated,
                _consumption_mode=consumption_mode,
            )
            async for event in stream:
                if isinstance(event, DocumentCompleted):
                    documents.append(event.document)
                elif isinstance(event, DocumentFailed):
                    failures.append(event)
            completed_at_dt = self._utcnow()
            results.append(
                PipelineResult(
                    source=source,
                    documents=documents,
                    errors=failures,
                    success_count=len(documents),
                    failure_count=len(failures),
                    started_at=started_at_dt,
                    completed_at=completed_at_dt,
                )
            )
        return results

    async def stream_events(
        self,
        source: str,
        *,
        params: Iterable[dict[str, Any]] | None = None,
        resume: bool = False,
        buffer_size: int = _DEFAULT_BUFFER_SIZE,
        progress_interval: int = _DEFAULT_PROGRESS_INTERVAL,
        checkpoint_interval: int = _DEFAULT_CHECKPOINT_INTERVAL,
        event_filter: EventFilter | None = None,
        event_transformer: EventTransformer | None = None,
        completed_ids: Iterable[str] | None = None,
        total_estimated: int | None = None,
        _consumption_mode: str | None = None,
    ) -> AsyncIterator[PipelineEvent]:
        """Stream structured pipeline events with backpressure support.

        The iterator yields :class:`PipelineEvent` subclasses describing
        lifecycle milestones, document outcomes, adapter state transitions, and
        progress updates. Callers can supply ``event_filter`` and
        ``event_transformer`` callbacks to declaratively tailor the stream.
        """

        mode = _consumption_mode or "stream_events"
        self._record_consumption(mode, source)
        pipeline_id = build_pipeline_id(source)
        queue: asyncio.Queue[PipelineEvent | object] = asyncio.Queue(maxsize=max(buffer_size, 1))
        sentinel = object()
        filter_fn: Callable[[PipelineEvent], bool]
        transform_fn: Callable[[PipelineEvent], PipelineEvent | None]
        filter_fn = event_filter or (lambda event: True)
        transform_fn = event_transformer or (lambda event: event)
        completed_total = 0
        failed_total = 0
        in_flight_count = 0
        checkpoint_target = checkpoint_interval if checkpoint_interval > 0 else None
        completed_checkpoint = 0
        estimated_total = total_estimated
        completed_skip = set(completed_ids or [])
        start_time = time.perf_counter()
        backpressure_wait_seconds = 0.0
        backpressure_wait_count = 0
        completed_since_checkpoint: list[str] = []
        last_checkpoint_at = start_time
        queue_gauge = PIPELINE_QUEUE_DEPTH.labels(adapter=source)
        queue_gauge.set(0.0)

        async def emit(event: PipelineEvent) -> None:
            transformed = transform_fn(event)
            if transformed is None:
                return
            if not filter_fn(transformed):
                return
            nonlocal backpressure_wait_seconds, backpressure_wait_count
            event_type = type(transformed).__name__
            PIPELINE_EVENT_COUNTER.labels(
                event_type=event_type, adapter=source
            ).inc()
            LOGGER.debug("pipeline_event", extra={"event": event_to_dict(transformed)})
            wait_started = time.perf_counter()
            await queue.put(transformed)
            waited = time.perf_counter() - wait_started
            if waited > 0:
                backpressure_wait_seconds += waited
                backpressure_wait_count += 1

        async def emit_progress(*, is_checkpoint: bool) -> None:
            nonlocal completed_since_checkpoint, last_checkpoint_at
            docs_for_checkpoint = (
                list(completed_since_checkpoint) if is_checkpoint else []
            )
            event = self._build_progress_event(
                pipeline_id,
                completed_total,
                failed_total,
                in_flight_count,
                estimated_total,
                start_time,
                queue.qsize(),
                queue.maxsize,
                backpressure_wait_seconds,
                backpressure_wait_count,
                docs_for_checkpoint,
                is_checkpoint,
            )
            queue_gauge.set(float(event.queue_depth))
            if is_checkpoint:
                latency = max(time.perf_counter() - last_checkpoint_at, 0.0)
                PIPELINE_CHECKPOINT_LATENCY.observe(latency)
                completed_since_checkpoint.clear()
                last_checkpoint_at = time.perf_counter()
            await emit(event)

        async def producer() -> None:
            nonlocal completed_total, failed_total, completed_checkpoint, in_flight_count
            state = "initial"
            await emit(
                AdapterStateChange(
                    timestamp=time.time(),
                    pipeline_id=pipeline_id,
                    adapter=source,
                    old_state=state,
                    new_state="initialising",
                    reason=None,
                )
            )
            state = "initialising"
            try:
                async with self._client_factory(**self._client_kwargs) as client:
                    adapter = self._resolve_adapter(source, client)
                    loop = asyncio.get_running_loop()

                    def _forward_adapter_event(event: PipelineEvent) -> None:
                        if not event.pipeline_id:
                            object.__setattr__(event, "pipeline_id", pipeline_id)
                        if not event.timestamp:
                            object.__setattr__(event, "timestamp", time.time())
                        task = loop.create_task(emit(event))
                        task.add_done_callback(lambda finished: finished.exception())

                    adapter.bind_event_emitter(_forward_adapter_event)
                    try:
                        await emit(
                            AdapterStateChange(
                                timestamp=time.time(),
                                pipeline_id=pipeline_id,
                                adapter=adapter.source,
                                old_state=state,
                                new_state="ready",
                                reason=None,
                            )
                        )
                        state = "ready"
                        for invocation in self._normalise_params(params):
                            invocation_params = dict(invocation or {})
                            await emit(
                                AdapterStateChange(
                                    timestamp=time.time(),
                                    pipeline_id=pipeline_id,
                                    adapter=adapter.source,
                                    old_state=state,
                                    new_state="invocation_started",
                                    reason=None,
                                )
                            )
                            state = "invocation_started"
                            keyword_args = dict(invocation_params)
                            if resume:
                                keyword_args.setdefault("resume", resume)
                            try:
                                async for result in adapter.iter_results(**keyword_args):
                                    document = result.document
                                    if document.doc_id in completed_skip:
                                        continue
                                    doc_started = time.perf_counter()
                                    await emit(
                                        DocumentStarted(
                                            timestamp=time.time(),
                                            pipeline_id=pipeline_id,
                                            doc_id=document.doc_id,
                                            adapter=adapter.source,
                                            parameters=dict(invocation_params),
                                        )
                                    )
                                    in_flight_count += 1
                                    duration = max(time.perf_counter() - doc_started, 0.0)
                                    await emit(
                                        DocumentCompleted(
                                            timestamp=time.time(),
                                            pipeline_id=pipeline_id,
                                            document=document,
                                            duration=duration,
                                            adapter_metadata=dict(result.metadata),
                                        )
                                    )
                                    completed_total += 1
                                    completed_since_checkpoint.append(document.doc_id)
                                    in_flight_count = max(in_flight_count - 1, 0)
                                    completed_checkpoint += 1
                                    if progress_interval > 0 and completed_total % progress_interval == 0:
                                        await emit_progress(is_checkpoint=False)
                                    if (
                                        checkpoint_target is not None
                                        and completed_checkpoint >= checkpoint_target
                                    ):
                                        completed_checkpoint = 0
                                        await emit_progress(is_checkpoint=True)
                            except Exception as exc:  # pragma: no cover - defensive
                                failed_total += 1
                                in_flight_count = max(in_flight_count - 1, 0)
                                completed_checkpoint += 1
                                await emit(
                                    DocumentFailed(
                                        timestamp=time.time(),
                                        pipeline_id=pipeline_id,
                                        doc_id=getattr(exc, "doc_id", None),
                                        error=str(exc),
                                        retry_count=getattr(exc, "retry_count", 0),
                                        is_retryable=bool(getattr(exc, "is_retryable", False)),
                                        error_type=exc.__class__.__name__,
                                        traceback=traceback.format_exc(),
                                    )
                                )
                                await emit(
                                    AdapterStateChange(
                                        timestamp=time.time(),
                                        pipeline_id=pipeline_id,
                                        adapter=adapter.source,
                                        old_state=state,
                                        new_state="failed",
                                        reason=str(exc),
                                    )
                                )
                                return
                            await emit(
                                AdapterStateChange(
                                    timestamp=time.time(),
                                    pipeline_id=pipeline_id,
                                    adapter=adapter.source,
                                    old_state=state,
                                    new_state="invocation_completed",
                                    reason=None,
                                )
                            )
                            state = "invocation_completed"
                    finally:
                        adapter.bind_event_emitter(None)
                await emit(
                    AdapterStateChange(
                        timestamp=time.time(),
                        pipeline_id=pipeline_id,
                        adapter=source,
                        old_state=state,
                        new_state="completed",
                        reason=None,
                    )
                )
            finally:
                await emit_progress(is_checkpoint=True)
                PIPELINE_DURATION_SECONDS.observe(
                    max(time.perf_counter() - start_time, 0.0)
                )
                await queue.put(sentinel)

        producer_task = asyncio.create_task(producer())

        try:
            while True:
                item = await queue.get()
                if item is sentinel:
                    break
                yield item  # type: ignore[misc]
        finally:
            queue_gauge.set(0.0)
            if not producer_task.done():
                producer_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await producer_task

    def _resolve_adapter(self, source: str, client: AsyncHttpClient) -> BaseAdapter[Any]:
        return self._registry.get_adapter(source, AdapterContext(ledger=self.ledger), client)

    @staticmethod
    def _normalise_params(
        params: Iterable[dict[str, Any]] | None,
    ) -> list[dict[str, Any] | None]:
        if params is None:
            return [None]
        normalised: list[dict[str, Any] | None] = []
        for entry in params:
            normalised.append(dict(entry))
        if not normalised:
            normalised.append({})
        return normalised

    @staticmethod
    def _build_progress_event(
        pipeline_id: str,
        completed_total: int,
        failed_total: int,
        in_flight_count: int,
        estimated_total: int | None,
        start_time: float,
        queue_depth: int,
        buffer_size: int,
        backpressure_wait_seconds: float,
        backpressure_wait_count: int,
        checkpoint_doc_ids: Sequence[str],
        is_checkpoint: bool,
    ) -> BatchProgress:
        elapsed = max(time.perf_counter() - start_time, 0.0)
        processed = completed_total + failed_total
        eta_seconds: float | None = None
        remaining: int | None = None
        if estimated_total is not None:
            remaining = max(estimated_total - processed, 0)
            if processed and elapsed > 0:
                rate = processed / elapsed
                if rate > 0:
                    eta_seconds = remaining / rate
        return BatchProgress(
            timestamp=time.time(),
            pipeline_id=pipeline_id,
            completed_count=completed_total,
            failed_count=failed_total,
            in_flight_count=max(in_flight_count, 0),
            queue_depth=max(queue_depth, 0),
            buffer_size=max(buffer_size, 1),
            remaining=remaining,
            eta_seconds=eta_seconds,
            backpressure_wait_seconds=max(backpressure_wait_seconds, 0.0),
            backpressure_wait_count=max(backpressure_wait_count, 0),
            checkpoint_doc_ids=list(checkpoint_doc_ids),
            is_checkpoint=is_checkpoint,
        )

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _record_consumption(mode: str, adapter: str) -> None:
        PIPELINE_CONSUMPTION_COUNTER.labels(mode=mode, adapter=adapter).inc()

    def __getattr__(self, attribute: str) -> Any:
        """Provide a clearer error for removed legacy helpers."""

        if attribute == "run_async_legacy":
            raise AttributeError(
                "IngestionPipeline.run_async_legacy() was removed; "
                "use stream_events() or run_async() instead."
            )
        message = f"{self.__class__.__name__!s} object has no attribute {attribute!r}"
        raise AttributeError(message)


__all__ = [
    "IngestionPipeline",
    "PipelineResult",
]
