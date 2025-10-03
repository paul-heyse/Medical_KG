"""Pipeline utilities orchestrating adapter execution and resume workflows."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from Medical_KG.ingestion import registry as ingestion_registry
from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.ledger import IngestionLedger
from Medical_KG.ingestion.models import Document


class AdapterRegistry(Protocol):
    def get_adapter(
        self,
        source: str,
        context: AdapterContext,
        client: AsyncHttpClient,
        **kwargs: Any,
    ) -> BaseAdapter[Any]:
        ...

    def available_sources(self) -> list[str]:
        ...


@dataclass(slots=True)
class PipelineResult:
    """Summarised ingestion execution details."""

    source: str
    doc_ids: list[str]


class IngestionPipeline:
    """Coordinate adapters, ledger interactions, and retry semantics."""

    def __init__(
        self,
        ledger: IngestionLedger,
        *,
        registry: AdapterRegistry | None = None,
        client_factory: type[AsyncHttpClient] | None = None,
    ) -> None:
        self.ledger = ledger
        self._registry = registry or ingestion_registry
        self._client_factory = client_factory or AsyncHttpClient

    def run(
        self,
        source: str,
        params: Iterable[dict[str, Any]] | None = None,
        *,
        resume: bool = False,
    ) -> list[PipelineResult]:
        """Execute an adapter for the supplied source synchronously."""

        return asyncio.run(self.run_async(source, params=params, resume=resume))

    async def run_async(
        self,
        source: str,
        *,
        params: Iterable[dict[str, Any]] | None = None,
        resume: bool = False,
    ) -> list[PipelineResult]:
        """Execute an adapter within an existing asyncio event loop."""

        outputs: list[PipelineResult] = []
        async with self._client_factory() as client:
            adapter = self._resolve_adapter(source, client)
            if params is None:
                doc_ids = [
                    result.document.doc_id
                    async for result in adapter.iter_results(resume=resume)
                ]
                outputs.append(PipelineResult(source=source, doc_ids=doc_ids))
            else:
                for entry in params:
                    invocation_params = dict(entry)
                    doc_ids = [
                        result.document.doc_id
                        async for result in adapter.iter_results(
                            **invocation_params, resume=resume
                        )
                    ]
                    outputs.append(PipelineResult(source=source, doc_ids=doc_ids))
        return outputs

    def status(self) -> dict[str, list[dict[str, Any]]]:
        summary: dict[str, list[dict[str, Any]]] = {}
        for entry in self.ledger.entries():
            summary.setdefault(entry.state, []).append(
                {"doc_id": entry.doc_id, "metadata": dict(entry.metadata)}
            )
        return summary

    def iter_results(
        self,
        source: str,
        *,
        params: Iterable[dict[str, Any]] | None = None,
        resume: bool = False,
    ) -> AsyncIterator[Document]:
        """Stream :class:`Document` instances as they are produced."""

        async def _generator() -> AsyncIterator[Document]:
            async with self._client_factory() as client:
                adapter = self._resolve_adapter(source, client)
                if params is None:
                    async for result in adapter.iter_results(resume=resume):
                        yield result.document
                else:
                    for entry in params:
                        invocation_params = dict(entry)
                        async for result in adapter.iter_results(
                            **invocation_params, resume=resume
                        ):
                            yield result.document

        return _generator()

    def _resolve_adapter(self, source: str, client: AsyncHttpClient) -> BaseAdapter[Any]:
        return self._registry.get_adapter(source, AdapterContext(ledger=self.ledger), client)

__all__ = [
    "IngestionPipeline",
    "PipelineResult",
]
