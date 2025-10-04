"""State machine backed ingestion ledger with compaction support."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from threading import Lock
from time import perf_counter
from typing import Iterable, Mapping, MutableMapping, Protocol, Sequence, cast

import jsonlines
from Medical_KG.compat.prometheus import Counter, Gauge, Histogram
from Medical_KG.ingestion.types import JSONMapping, JSONValue, MutableJSONMapping
from Medical_KG.ingestion.utils import ensure_json_value

LOGGER = logging.getLogger(__name__)

STATE_TRANSITION_COUNTER = Counter(
    "med_ledger_state_transitions_total",
    "Number of ledger state transitions by old/new state",
    labelnames=("from_state", "to_state"),
)
INITIALIZATION_COUNTER = Counter(
    "med_ledger_initialization_total",
    "Ledger initialization calls partitioned by load method",
    labelnames=("method",),
)
INITIALIZATION_DURATION = Histogram(
    "med_ledger_initialization_seconds",
    "Ledger initialization wall clock duration",
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30, 60),
)
STATE_DISTRIBUTION = Gauge(
    "med_ledger_documents_by_state",
    "Current documents per ledger state",
    labelnames=("state",),
)
STUCK_DOCUMENTS = Gauge(
    "med_ledger_stuck_documents",
    "Documents exceeding stuck threshold in non-terminal states",
    labelnames=("state",),
)
STATE_DURATION = Histogram(
    "med_ledger_state_duration_seconds",
    "Observed duration spent in ledger states before transitioning",
    buckets=(0.1, 0.5, 1, 2, 5, 10, 30, 60, 300, 900, 3600, 14400, 86400),
)
ERROR_COUNTER = Counter(
    "med_ledger_errors_total",
    "Count of critical ledger errors",
    labelnames=("type",),
)


class LedgerError(RuntimeError):
    """Base exception for ledger errors."""


class InvalidStateTransition(LedgerError):
    """Raised when attempting an invalid state transition."""


class LedgerCorruption(LedgerError):
    """Raised when ledger data on disk cannot be parsed safely."""


class _JsonLinesWriter(Protocol):
    def write(self, obj: object) -> None:
        ...


class LedgerState(str, Enum):
    """Enumeration of all valid ledger states.

    The state machine captures the canonical ingestion pipeline phases. Ledger
    states serialise to their enum name for audit records and snapshots.
    """

    PENDING = "pending"
    """Document enqueued but not yet processed."""

    FETCHING = "fetching"
    """Actively retrieving the raw document payload from the upstream source."""

    FETCHED = "fetched"
    """Document payload successfully downloaded and staged for parsing."""

    PARSING = "parsing"
    """Running structural parsing (PDF/OA parsing, adapter specific decoding)."""

    PARSED = "parsed"
    """Parsing complete; structured payload available for validation."""

    VALIDATING = "validating"
    """Performing schema and contract validation on the parsed payload."""

    VALIDATED = "validated"
    """Validation succeeded; the document is ready for IR construction."""

    IR_BUILDING = "ir_building"
    """Constructing intermediate representation objects."""

    IR_READY = "ir_ready"
    """Intermediate representation written and ready for downstream tasks."""

    EMBEDDING = "embedding"
    """Generating dense/sparse embeddings from the IR."""

    INDEXED = "indexed"
    """Embeddings persisted to the search index."""

    COMPLETED = "completed"
    """Document fully processed and available for search."""

    FAILED = "failed"
    """Processing failed with a non-recoverable error."""

    RETRYING = "retrying"
    """Waiting to retry after a recoverable error."""

    SKIPPED = "skipped"
    """Processing skipped (manually or because the document is obsolete)."""


VALID_TRANSITIONS: Mapping[LedgerState, set[LedgerState]] = {
    LedgerState.PENDING: {LedgerState.FETCHING, LedgerState.SKIPPED},
    LedgerState.FETCHING: {
        LedgerState.FETCHED,
        LedgerState.FAILED,
        LedgerState.RETRYING,
    },
    LedgerState.FETCHED: {LedgerState.PARSING, LedgerState.FAILED},
    LedgerState.PARSING: {LedgerState.PARSED, LedgerState.FAILED},
    LedgerState.PARSED: {LedgerState.VALIDATING, LedgerState.FAILED},
    LedgerState.VALIDATING: {LedgerState.VALIDATED, LedgerState.FAILED},
    LedgerState.VALIDATED: {LedgerState.IR_BUILDING, LedgerState.FAILED},
    LedgerState.IR_BUILDING: {LedgerState.IR_READY, LedgerState.FAILED},
    LedgerState.IR_READY: {
        LedgerState.EMBEDDING,
        LedgerState.COMPLETED,
        LedgerState.FAILED,
    },
    LedgerState.EMBEDDING: {
        LedgerState.INDEXED,
        LedgerState.COMPLETED,
        LedgerState.FAILED,
    },
    LedgerState.INDEXED: {LedgerState.COMPLETED, LedgerState.FAILED},
    LedgerState.RETRYING: {LedgerState.FETCHING, LedgerState.FAILED},
    LedgerState.FAILED: {LedgerState.RETRYING, LedgerState.FAILED},
    LedgerState.SKIPPED: set(),
    LedgerState.COMPLETED: set(),
}

_PERSISTED_STATE_ALIASES: Mapping[str, LedgerState] = {
    "auto_done": LedgerState.COMPLETED,
    "auto_failed": LedgerState.FAILED,
    "auto_inflight": LedgerState.FETCHING,
    "mineru_failed": LedgerState.FAILED,
    "mineru_inflight": LedgerState.IR_BUILDING,
    "pdf_downloaded": LedgerState.FETCHED,
    "pdf_ir_ready": LedgerState.IR_READY,
    "ir_exists": LedgerState.IR_READY,
    "ir_written": LedgerState.IR_READY,
    "postpdf_started": LedgerState.EMBEDDING,
}

TERMINAL_STATES: set[LedgerState] = {
    LedgerState.COMPLETED,
    LedgerState.FAILED,
    LedgerState.SKIPPED,
}

RETRYABLE_STATES: set[LedgerState] = {
    LedgerState.FETCHING,
    LedgerState.FETCHED,
    LedgerState.PARSING,
    LedgerState.PARSED,
    LedgerState.VALIDATING,
    LedgerState.VALIDATED,
    LedgerState.IR_BUILDING,
    LedgerState.IR_READY,
    LedgerState.EMBEDDING,
    LedgerState.INDEXED,
    LedgerState.FAILED,
}

STATE_MACHINE_DOC = """
State Machine:

    [PENDING] ──▶ [FETCHING] ──▶ [FETCHED] ──▶ [PARSING] ──▶ [PARSED] ──▶ [VALIDATING]
         │             │              │             │             │             │
         │             │              │             │             │             ▼
         │             ▼              ▼             ▼             ▼         [FAILED]
         └────────▶ [SKIPPED]      [FAILED]     [FAILED]       [FAILED]

    [VALIDATED] ──▶ [IR_BUILDING] ──▶ [IR_READY] ──▶ [EMBEDDING] ──▶ [INDEXED] ──▶ [COMPLETED]
                                           │             │              │
                                           │             │              ▼
                                           │             │          [FAILED]
                                           │             ▼
                                           │         [FAILED]
                                           ▼
                                       [FAILED]

    Retry loop: any retryable state ──▶ [RETRYING] ──▶ [FETCHING]
""".strip()


def _ensure_ledger_state(value: object, *, argument: str) -> LedgerState:
    if isinstance(value, LedgerState):
        return value
    raise TypeError(
        f"{argument} must be a LedgerState instance (received {value!r}). "
        "Use the LedgerState enum, e.g. LedgerState.COMPLETED."
    )


def _decode_state(
    raw: JSONValue,
    *,
    context: str,
    legacy_fallback: LedgerState | None = None,
) -> LedgerState:
    if isinstance(raw, LedgerState):
        return raw
    if isinstance(raw, str):
        token = raw.strip()
        if not token:
            raise LedgerCorruption(f"{context} is missing a ledger state")
        alias = _PERSISTED_STATE_ALIASES.get(token.lower())
        if alias is not None:
            return alias
        upper_token = token.upper()
        try:
            return LedgerState[upper_token]
        except KeyError:
            lower_token = token.lower()
            if lower_token == "legacy":
                if legacy_fallback is not None:
                    return legacy_fallback
                raise LedgerCorruption(
                    f"{context} references removed legacy state without fallback"
                )
            try:
                return LedgerState(lower_token)
            except ValueError as exc:
                raise LedgerCorruption(
                    f"{context} contains unknown ledger state: {token!r}"
                ) from exc
    raise LedgerCorruption(f"{context} is not a valid ledger state")


def get_valid_next_states(current: LedgerState) -> set[LedgerState]:
    """Return the allowed next states for ``current``."""

    return set(VALID_TRANSITIONS.get(current, set()))


def is_terminal_state(state: LedgerState) -> bool:
    """Return ``True`` if the state is terminal."""

    return state in TERMINAL_STATES


def is_retryable_state(state: LedgerState) -> bool:
    """Return ``True`` if the state can transition to :class:`LedgerState.RETRYING`."""

    return state in RETRYABLE_STATES


def validate_transition(old: LedgerState, new: LedgerState) -> None:
    """Validate the ``old`` -> ``new`` transition.

    The function tolerates no-op transitions and raises
    :class:`InvalidStateTransition` when the transition is not declared in
    :data:`VALID_TRANSITIONS`.
    """

    if old == new:
        return
    allowed = VALID_TRANSITIONS.get(old, set())
    if new not in allowed:
        raise InvalidStateTransition(
            f"Invalid ledger state transition: {old.value!r} -> {new.value!r}"
        )


@dataclass(slots=True)
class LedgerAuditRecord:
    """Structured audit trail for ledger state transitions."""

    doc_id: str
    old_state: LedgerState
    new_state: LedgerState
    timestamp: float
    adapter: str | None
    error_type: str | None = None
    error_message: str | None = None
    traceback: str | None = None
    retry_count: int | None = None
    duration_seconds: float | None = None
    parameters: JSONMapping = field(default_factory=dict)
    metadata: JSONMapping = field(default_factory=dict)

    def to_dict(self) -> JSONMapping:
        """Serialize audit record for JSONL persistence."""

        payload: JSONMapping = {
            "doc_id": self.doc_id,
            "old_state": self.old_state.name,
            "new_state": self.new_state.name,
            "timestamp": self.timestamp,
            "adapter": self.adapter,
            "error_type": self.error_type,
            "error_message": self.error_message,
            "traceback": self.traceback,
            "retry_count": self.retry_count,
            "duration_seconds": self.duration_seconds,
            "parameters": self.parameters,
            "metadata": self.metadata,
        }
        return payload

    @classmethod
    def from_dict(cls, payload: Mapping[str, JSONValue]) -> "LedgerAuditRecord":
        """Rehydrate an audit record from a JSON mapping."""

        try:
            new_state = _decode_state(payload["new_state"], context="audit new_state")
            old_state = _decode_state(
                payload["old_state"],
                context="audit old_state",
                legacy_fallback=new_state,
            )
        except (KeyError, ValueError) as exc:  # pragma: no cover - defensive guard
            raise LedgerCorruption("Ledger audit record has invalid state") from exc
        timestamp_raw = payload.get("timestamp")
        timestamp = _as_float(timestamp_raw)
        metadata_value = ensure_json_value(payload.get("metadata", {}), context="ledger audit metadata")
        if isinstance(metadata_value, Mapping):
            metadata = cast(MutableJSONMapping, metadata_value)
        else:
            metadata = cast(MutableJSONMapping, {})
        parameters_value = ensure_json_value(payload.get("parameters", {}), context="ledger audit parameters")
        if isinstance(parameters_value, Mapping):
            parameters = cast(MutableJSONMapping, parameters_value)
        else:
            parameters = cast(MutableJSONMapping, {})
        return cls(
            doc_id=str(payload["doc_id"]),
            old_state=old_state,
            new_state=new_state,
            timestamp=timestamp,
            adapter=str(payload.get("adapter")) if payload.get("adapter") else None,
            error_type=str(payload.get("error_type")) if payload.get("error_type") else None,
            error_message=str(payload.get("error_message"))
            if payload.get("error_message")
            else None,
            traceback=str(payload.get("traceback")) if payload.get("traceback") else None,
            retry_count=_as_int(payload.get("retry_count")),
            duration_seconds=_as_float(payload.get("duration_seconds")),
            parameters=parameters,
            metadata=metadata,
        )


@dataclass(slots=True)
class LedgerDocumentState:
    """Latest state for a document tracked by the ledger."""

    doc_id: str
    state: LedgerState
    updated_at: datetime
    adapter: str | None = None
    metadata: JSONMapping = field(default_factory=dict)
    retry_count: int = 0
    history: list[LedgerAuditRecord] = field(default_factory=list)

    def duration(self, *, as_of: datetime | None = None) -> float:
        """Return seconds spent in the current state."""

        reference = as_of or datetime.now(timezone.utc)
        return (reference - self.updated_at).total_seconds()


def _as_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _as_int(value: object, default: int | None = None) -> int | None:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default


class IngestionLedger:
    """Durable ledger with validated state machine and compaction."""

    def __init__(
        self,
        path: Path,
        *,
        snapshot_dir: Path | None = None,
        auto_snapshot_interval: timedelta | None = None,
        snapshot_retention: int = 7,
    ) -> None:
        self._path = path
        self._lock = Lock()
        self._snapshot_dir = snapshot_dir or path.with_suffix(".snapshots")
        self._auto_snapshot_interval = auto_snapshot_interval or timedelta(days=1)
        self._snapshot_retention = snapshot_retention
        self._documents: dict[str, LedgerDocumentState] = {}
        self._history: dict[str, list[LedgerAuditRecord]] = {}
        self._last_snapshot_at: datetime | None = None
        self._load()

    # ------------------------------------------------------------------ loading
    def _load(self) -> None:
        start = perf_counter()
        method = "full"
        snapshot = self._latest_snapshot()
        records: dict[str, LedgerDocumentState] = {}
        history: dict[str, list[LedgerAuditRecord]] = {}
        if snapshot:
            method = "snapshot"
            INITIALIZATION_COUNTER.labels(method=method).inc()
            snapshot_states, snapshot_history, created_at = self.load_snapshot(snapshot)
            records.update(snapshot_states)
            history.update(snapshot_history)
            self._last_snapshot_at = created_at
        else:
            INITIALIZATION_COUNTER.labels(method=method).inc()
        try:
            if self._path.exists():
                with jsonlines.open(self._path, mode="r") as fp:
                    for row in cast(Iterable[Mapping[str, JSONValue]], fp):
                        audit = LedgerAuditRecord.from_dict(row)
                        validate_transition(audit.old_state, audit.new_state)
                        state = records.get(
                            audit.doc_id,
                            LedgerDocumentState(
                                doc_id=audit.doc_id,
                                state=audit.old_state,
                                updated_at=datetime.fromtimestamp(
                                    audit.timestamp, tz=timezone.utc
                                ),
                            ),
                        )
                        self._apply_audit(state, audit)
                        records[audit.doc_id] = state
                        history.setdefault(audit.doc_id, []).append(audit)
        except Exception as exc:  # pragma: no cover - defensive
            raise LedgerCorruption("Ledger JSONL file is malformed") from exc
        except InvalidStateTransition as exc:  # pragma: no cover - defensive
            raise LedgerCorruption("Ledger contains invalid transition") from exc
        self._documents = records
        self._history = history
        INITIALIZATION_DURATION.observe(perf_counter() - start)
        self._refresh_state_metrics()

    def load_snapshot(
        self, snapshot_path: Path
    ) -> tuple[dict[str, LedgerDocumentState], dict[str, list[LedgerAuditRecord]], datetime]:
        with snapshot_path.open("r", encoding="utf-8") as handle:
            snapshot = json.load(handle)
        if not isinstance(snapshot, MutableMapping):  # pragma: no cover - defensive
            raise LedgerCorruption("Snapshot must be a JSON object")
        version = snapshot.get("version")
        if version != "1.0":  # pragma: no cover - defensive
            raise LedgerCorruption(f"Unsupported snapshot version: {version}")
        created_at_raw = snapshot.get("created_at")
        created_at = datetime.fromisoformat(str(created_at_raw)) if created_at_raw else datetime.now(timezone.utc)
        states: dict[str, LedgerDocumentState] = {}
        history: dict[str, list[LedgerAuditRecord]] = {}
        raw_states = snapshot.get("states", {})
        if not isinstance(raw_states, Mapping):  # pragma: no cover - defensive
            raise LedgerCorruption("Snapshot states must be a mapping")
        for doc_id, payload in raw_states.items():
            if not isinstance(payload, Mapping):  # pragma: no cover - defensive
                continue
            updated_at_raw = payload.get("updated_at")
            updated_at = datetime.fromisoformat(str(updated_at_raw)) if updated_at_raw else created_at
            metadata_value = ensure_json_value(payload.get("metadata", {}), context="snapshot metadata")
            if isinstance(metadata_value, Mapping):
                metadata = cast(MutableJSONMapping, metadata_value)
            else:
                metadata = cast(MutableJSONMapping, {})
            retry_count = _as_int(payload.get("retry_count"), default=0) or 0
            adapter_value = payload.get("adapter")
            history_payload = payload.get("history", [])
            audits: list[LedgerAuditRecord] = []
            if isinstance(history_payload, Sequence):
                for entry in history_payload:
                    if isinstance(entry, Mapping):
                        audits.append(LedgerAuditRecord.from_dict(entry))
            state_raw = payload.get("state")
            if state_raw is None and audits:
                state_value = audits[-1].new_state
            else:
                state_value = _decode_state(
                    state_raw,
                    context=f"snapshot state for {doc_id}",
                    legacy_fallback=audits[-1].new_state if audits else None,
                )
            document_state = LedgerDocumentState(
                doc_id=str(doc_id),
                state=state_value,
                updated_at=updated_at,
                adapter=str(adapter_value) if adapter_value else None,
                metadata=metadata,
                retry_count=retry_count,
            )
            if audits:
                document_state.history.extend(audits)
            states[document_state.doc_id] = document_state
            if audits:
                history[document_state.doc_id] = audits
        return states, history, created_at

    def load_with_compaction(self, snapshot_path: Path, delta_path: Path) -> dict[str, LedgerDocumentState]:
        states, history, _created = self.load_snapshot(snapshot_path)
        with jsonlines.open(delta_path, mode="r") as fp:
            for row in cast(Iterable[Mapping[str, JSONValue]], fp):
                audit = LedgerAuditRecord.from_dict(row)
                state = states.get(
                    audit.doc_id,
                    LedgerDocumentState(
                        doc_id=audit.doc_id,
                        state=audit.old_state,
                        updated_at=datetime.fromtimestamp(audit.timestamp, tz=timezone.utc),
                    ),
                )
                self._apply_audit(state, audit)
                states[audit.doc_id] = state
                history.setdefault(audit.doc_id, []).append(audit)
        return states

    def _latest_snapshot(self) -> Path | None:
        if not self._snapshot_dir.exists():
            return None
        snapshots = sorted(self._snapshot_dir.glob("*.json"))
        if not snapshots:
            return None
        return snapshots[-1]

    # ---------------------------------------------------------------- transitions
    def update_state(
        self,
        doc_id: str,
        new_state: LedgerState,
        *,
        adapter: str | None = None,
        metadata: Mapping[str, JSONValue] | None = None,
        error: BaseException | None = None,
        error_type: str | None = None,
        error_message: str | None = None,
        traceback: str | None = None,
        retry_count: int | None = None,
        duration_seconds: float | None = None,
        parameters: Mapping[str, JSONValue] | None = None,
    ) -> LedgerAuditRecord:
        """Transition ``doc_id`` to ``new_state`` and persist audit trail."""

        new_state = _ensure_ledger_state(new_state, argument="new_state")
        with self._lock:
            document = self._documents.get(doc_id)
            if document is None:
                old_state = new_state
            else:
                old_state = document.state
                try:
                    validate_transition(old_state, new_state)
                except InvalidStateTransition:
                    ERROR_COUNTER.labels(type="invalid_transition").inc()
                    LOGGER.error(
                        "Invalid ledger transition",
                        extra={
                            "doc_id": doc_id,
                            "old_state": old_state.value,
                            "new_state": new_state.value,
                            "adapter": adapter,
                        },
                    )
                    raise
            now = datetime.now(timezone.utc)
            timestamp = now.timestamp()
            resolved_error_type = error_type
            resolved_error_message = error_message
            if error is not None:
                resolved_error_type = error.__class__.__name__
                resolved_error_message = str(error)
            try:
                audit = LedgerAuditRecord(
                    doc_id=doc_id,
                    old_state=old_state,
                    new_state=new_state,
                    timestamp=timestamp,
                    adapter=adapter,
                    error_type=resolved_error_type,
                    error_message=resolved_error_message,
                    traceback=traceback,
                    retry_count=retry_count,
                    duration_seconds=duration_seconds,
                    parameters=dict(parameters) if parameters is not None else {},
                    metadata=dict(metadata) if metadata is not None else {},
                )
            except Exception:  # pragma: no cover - defensive
                ERROR_COUNTER.labels(type="audit_serialization").inc()
                LOGGER.exception(
                    "Failed to construct ledger audit record",
                    extra={"doc_id": doc_id, "adapter": adapter},
                )
                raise
            STATE_TRANSITION_COUNTER.labels(
                from_state=audit.old_state.value, to_state=audit.new_state.value
            ).inc()
            try:
                if document is None:
                    document = LedgerDocumentState(
                        doc_id=doc_id,
                        state=new_state,
                        updated_at=now,
                        adapter=adapter,
                        metadata=dict(metadata) if metadata is not None else {},
                        retry_count=retry_count or 0,
                        history=[audit],
                    )
                    self._documents[doc_id] = document
                else:
                    if duration_seconds is None:
                        duration_seconds = document.duration(as_of=now)
                    document.state = new_state
                    document.updated_at = now
                    document.adapter = adapter or document.adapter
                    if metadata is not None:
                        document.metadata = dict(metadata)
                    if retry_count is not None:
                        document.retry_count = retry_count
                    document.history.append(audit)
                self._history.setdefault(doc_id, []).append(audit)
                if duration_seconds is not None:
                    STATE_DURATION.observe(duration_seconds)
                self._write_audit(audit)
            except Exception:
                ERROR_COUNTER.labels(type="update_state").inc()
                LOGGER.exception(
                    "Ledger update failed",
                    extra={
                        "doc_id": doc_id,
                        "old_state": old_state.value,
                        "new_state": new_state.value,
                        "adapter": adapter,
                    },
                )
                raise
            LOGGER.info(
                "Ledger state transition",
                extra={
                    "doc_id": doc_id,
                    "old_state": old_state.value,
                    "new_state": new_state.value,
                    "adapter": adapter,
                },
            )
            self._refresh_state_metrics()
            self._maybe_snapshot(now)
            return audit

    def record(
        self,
        doc_id: str,
        state: LedgerState,
        metadata: Mapping[str, JSONValue] | None = None,
        *,
        adapter: str | None = None,
        error: BaseException | None = None,
        retry_count: int | None = None,
        duration_seconds: float | None = None,
        parameters: Mapping[str, JSONValue] | None = None,
    ) -> LedgerAuditRecord:
        """Alias for :meth:`update_state` requiring :class:`LedgerState`."""

        coerced = _ensure_ledger_state(state, argument="state")
        return self.update_state(
            doc_id,
            coerced,
            adapter=adapter,
            metadata=metadata,
            error=error,
            retry_count=retry_count,
            duration_seconds=duration_seconds,
            parameters=parameters,
        )

    def get(self, doc_id: str) -> LedgerDocumentState | None:
        return self._documents.get(doc_id)

    def get_state(self, doc_id: str) -> LedgerState | None:
        document = self._documents.get(doc_id)
        return document.state if document else None

    def entries(self, *, state: LedgerState | None = None) -> Iterable[LedgerDocumentState]:
        if state is None:
            return list(self._documents.values())
        coerced = _ensure_ledger_state(state, argument="state")
        return [document for document in self._documents.values() if document.state == coerced]

    def get_documents_by_state(self, state: LedgerState) -> list[LedgerDocumentState]:
        coerced = _ensure_ledger_state(state, argument="state")
        return [document for document in self._documents.values() if document.state == coerced]

    def get_state_history(self, doc_id: str) -> list[LedgerAuditRecord]:
        return list(self._history.get(doc_id, []))

    def get_state_duration(self, doc_id: str) -> float:
        document = self._documents.get(doc_id)
        if not document:
            return 0.0
        return document.duration()

    def get_stuck_documents(self, threshold_hours: int) -> list[LedgerDocumentState]:
        threshold_seconds = threshold_hours * 3600
        stuck: list[LedgerDocumentState] = []
        for document in self._documents.values():
            if is_terminal_state(document.state):
                continue
            duration = document.duration()
            if duration >= threshold_seconds:
                stuck.append(document)
        for state in LedgerState:
            if state in TERMINAL_STATES:
                STUCK_DOCUMENTS.labels(state=state.value).set(0)
                continue
            count = sum(1 for doc in stuck if doc.state is state)
            STUCK_DOCUMENTS.labels(state=state.value).set(count)
        if stuck:
            LOGGER.warning(
                "Stuck ledger documents detected",
                extra={
                    "count": len(stuck),
                    "threshold_hours": threshold_hours,
                    "states": [doc.state.value for doc in stuck],
                },
            )
        return stuck

    # ---------------------------------------------------------------- snapshots
    def create_snapshot(self, output_path: Path | None = None) -> Path:
        snapshot_path = output_path or self._snapshot_dir / f"snapshot-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        payload: MutableJSONMapping = {
            "version": "1.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "document_count": len(self._documents),
            "states": {},
        }
        states_payload: dict[str, JSONMapping] = {}
        for doc in self._documents.values():
            states_payload[doc.doc_id] = {
                "state": doc.state.name,
                "updated_at": doc.updated_at.isoformat(),
                "adapter": doc.adapter,
                "metadata": doc.metadata,
                "retry_count": doc.retry_count,
                "history": [audit.to_dict() for audit in doc.history],
            }
        payload["states"] = states_payload
        with snapshot_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        self._last_snapshot_at = datetime.now(timezone.utc)
        self._rotate_snapshots()
        self._truncate_ledger()
        LOGGER.info("Ledger snapshot created", extra={"snapshot": str(snapshot_path)})
        return snapshot_path

    def load_snapshot_file(self, snapshot_path: Path) -> None:
        states, history, created_at = self.load_snapshot(snapshot_path)
        self._documents = states
        self._history = history
        self._last_snapshot_at = created_at
        self._refresh_state_metrics()

    def load_with_snapshot(self, snapshot_path: Path, delta_path: Path) -> None:
        states = self.load_with_compaction(snapshot_path, delta_path)
        self._documents = states
        self._history.clear()
        for document in states.values():
            self._history[document.doc_id] = list(document.history)
        self._refresh_state_metrics()

    def load_snapshot_if_present(self) -> None:
        snapshot = self._latest_snapshot()
        if snapshot:
            self.load_snapshot_file(snapshot)

    def _truncate_ledger(self) -> None:
        if not self._path.exists():
            return
        self._path.write_text("", encoding="utf-8")

    def _rotate_snapshots(self) -> None:
        snapshots = sorted(self._snapshot_dir.glob("*.json"))
        if len(snapshots) <= self._snapshot_retention:
            return
        for old in snapshots[: -self._snapshot_retention]:
            old.unlink(missing_ok=True)

    def _maybe_snapshot(self, now: datetime) -> None:
        if not self._auto_snapshot_interval:
            return
        if self._last_snapshot_at is None:
            self._last_snapshot_at = now
            return
        if now - self._last_snapshot_at >= self._auto_snapshot_interval:
            self.create_snapshot()

    # ---------------------------------------------------------------- utilities
    def _apply_audit(self, document: LedgerDocumentState, audit: LedgerAuditRecord) -> None:
        document.state = audit.new_state
        document.updated_at = datetime.fromtimestamp(audit.timestamp, tz=timezone.utc)
        document.adapter = audit.adapter or document.adapter
        if audit.metadata:
            document.metadata = audit.metadata
        if audit.retry_count is not None:
            document.retry_count = audit.retry_count
        document.history.append(audit)

    def _write_audit(self, audit: LedgerAuditRecord) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with jsonlines.open(self._path, mode="a") as fp:
            cast(_JsonLinesWriter, fp).write(audit.to_dict())

    def _refresh_state_metrics(self) -> None:
        for state in LedgerState:
            count = sum(1 for document in self._documents.values() if document.state is state)
            STATE_DISTRIBUTION.labels(state=state.value).set(count)


# --------------------------------------------------------------------------- API

__all__ = [
    "IngestionLedger",
    "InvalidStateTransition",
    "LedgerAuditRecord",
    "LedgerCorruption",
    "LedgerDocumentState",
    "LedgerError",
    "LedgerState",
    "STATE_MACHINE_DOC",
    "TERMINAL_STATES",
    "RETRYABLE_STATES",
    "get_valid_next_states",
    "is_retryable_state",
    "is_terminal_state",
    "validate_transition",
]
