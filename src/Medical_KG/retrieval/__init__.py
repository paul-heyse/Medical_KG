"""Retrieval orchestration package."""

from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

from .clients import (
    ConstantEmbeddingClient,
    EmbeddingClient,
    InMemorySearch,
    InMemorySearchHit,
    InMemoryVector,
    OpenSearchClient,
    PassthroughEncoder,
    Reranker,
    SpladeEncoder,
    VectorSearchClient,
)
from .intent import IntentClassifier, IntentRule
from .models import RetrievalRequest, RetrievalResponse
from .ontology import ConceptCatalogClient, OntologyExpander, OntologyTerm
from .service import RetrievalService, RetrieverConfig

if TYPE_CHECKING:
    from .api import create_router
else:  # pragma: no cover - optional FastAPI dependency
    try:
        from .api import create_router
    except ModuleNotFoundError:

        def create_router(service: RetrievalService) -> NoReturn:  # pragma: no cover - fallback
            raise RuntimeError("FastAPI integration is unavailable: fastapi not installed")


__all__ = [
    "create_router",
    "RetrievalService",
    "RetrieverConfig",
    "IntentClassifier",
    "IntentRule",
    "OntologyExpander",
    "OntologyTerm",
    "ConceptCatalogClient",
    "EmbeddingClient",
    "OpenSearchClient",
    "VectorSearchClient",
    "SpladeEncoder",
    "Reranker",
    "InMemorySearch",
    "InMemorySearchHit",
    "InMemoryVector",
    "PassthroughEncoder",
    "ConstantEmbeddingClient",
    "RetrievalRequest",
    "RetrievalResponse",
]
