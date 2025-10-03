"""Pipeline utilities orchestrating adapter execution and resume workflows."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.ledger import IngestionLedger
from Medical_KG.ingestion import registry as ingestion_registry


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
        registry: Any | None = None,
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

        return asyncio.run(self._run_async(source, params=params, resume=resume))

    async def _run_async(
        self,
        source: str,
        *,
        params: Iterable[dict[str, Any]] | None = None,
        resume: bool = False,
    ) -> list[PipelineResult]:
        client = self._client_factory()
        adapter = self._resolve_adapter(source, client)
        outputs: list[PipelineResult] = []
        try:
            if params is None:
                results = await self._invoke(adapter, {}, resume=resume)
                outputs.append(PipelineResult(source=source, doc_ids=results))
            else:
                for entry in params:
                    results = await self._invoke(adapter, entry, resume=resume)
                    outputs.append(PipelineResult(source=source, doc_ids=results))
        finally:
            await client.aclose()
        return outputs

    def status(self) -> dict[str, list[dict[str, Any]]]:
        summary: dict[str, list[dict[str, Any]]] = {}
        for entry in self.ledger.entries():
            summary.setdefault(entry.state, []).append(
                {"doc_id": entry.doc_id, "metadata": dict(entry.metadata)}
            )
        return summary

    async def _invoke(
        self,
        adapter: BaseAdapter,
        params: dict[str, Any],
        *,
        resume: bool,
    ) -> list[str]:
        invocation_params = dict(params)
        invocation_params["resume"] = resume
        results = list(await adapter.run(**invocation_params))
        return [result.document.doc_id for result in results]

    def _resolve_adapter(self, source: str, client: AsyncHttpClient) -> BaseAdapter:
        return self._registry.get_adapter(source, AdapterContext(ledger=self.ledger), client)

__all__ = [
    "IngestionPipeline",
    "PipelineResult",
]
