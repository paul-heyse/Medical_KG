from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Iterator, Mapping

import httpx

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.ledger import LedgerEntry
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.utils import generate_doc_id

_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "ingestion"


def load_json_fixture(name: str) -> Any:
    path = _FIXTURES_DIR / name
    return json.loads(path.read_text(encoding="utf-8"))


def load_text_fixture(name: str) -> str:
    path = _FIXTURES_DIR / name
    return path.read_text(encoding="utf-8")


def make_adapter_context(ledger: "FakeLedger") -> AdapterContext:
    """Construct an :class:`AdapterContext` bound to the provided ledger."""

    return AdapterContext(ledger=ledger)  # type: ignore[arg-type]


@dataclass(slots=True)
class FakeLedger:
    """In-memory replacement for :class:`IngestionLedger` used in tests."""

    _entries: list[LedgerEntry]

    def __init__(self) -> None:
        self._entries = []

    def record(self, doc_id: str, state: str, metadata: Mapping[str, Any] | None = None) -> LedgerEntry:
        entry = LedgerEntry(
            doc_id=doc_id,
            state=state,
            timestamp=datetime.now(timezone.utc),
            metadata=dict(metadata or {}),
        )
        self._entries.append(entry)
        return entry

    def get(self, doc_id: str) -> LedgerEntry | None:
        for entry in reversed(self._entries):
            if entry.doc_id == doc_id:
                return entry
        return None

    def entries(self, *, state: str | None = None) -> Iterable[LedgerEntry]:
        if state is None:
            return list(self._entries)
        return [entry for entry in self._entries if entry.state == state]


class FakeRegistry:
    """Minimal registry that returns pre-wired adapters for CLI tests."""

    def __init__(self, adapters: Mapping[str, Callable[[AdapterContext, Any], Any]]) -> None:
        self._adapters = dict(adapters)
        self.calls: list[tuple[str, Mapping[str, Any]]] = []

    def available_sources(self) -> list[str]:
        return sorted(self._adapters)

    def get_adapter(self, source: str, context: AdapterContext, client: Any, **kwargs: Any) -> Any:
        factory = self._adapters[source]
        adapter = factory(context, client)
        self.calls.append((source, kwargs))
        return adapter


def sample_document_factory(source: str = "test") -> Callable[[str, str], Document]:
    """Return a factory that builds deterministic :class:`Document` instances."""

    def _factory(identifier: str, content: str, **metadata: Any) -> Document:
        doc_id = generate_doc_id(source, identifier, metadata.get("version", "v1"), content.encode("utf-8"))
        meta = dict(metadata)
        meta.setdefault("identifier", identifier)
        return Document(doc_id=doc_id, source=source, content=content, metadata=meta)

    return _factory


def build_mock_transport(responders: Iterable[httpx.Response | Callable[[httpx.Request], httpx.Response]]) -> httpx.MockTransport:
    """Create a :class:`httpx.MockTransport` that iterates over canned responses."""

    iterator: Iterator[httpx.Response | Callable[[httpx.Request], httpx.Response]] = iter(responders)

    def _handler(request: httpx.Request) -> httpx.Response:
        try:
            responder = next(iterator)
        except StopIteration as exc:  # pragma: no cover - defensive guard for misconfigured tests
            raise AssertionError("Mock transport received more requests than expected") from exc
        if callable(responder):
            return responder(request)
        return responder

    return httpx.MockTransport(_handler)

