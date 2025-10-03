"""Retrieval orchestration package."""
from __future__ import annotations

from typing import TYPE_CHECKING, NoReturn

from .service import RetrievalService, RetrieverConfig
from .intent import IntentClassifier, IntentRule
from .ontology import OntologyExpander, OntologyTerm, ConceptCatalogClient
from .clients import (
    EmbeddingClient,
    OpenSearchClient,
    VectorSearchClient,
    SpladeEncoder,
    Reranker,
    InMemorySearch,
    InMemorySearchHit,
    InMemoryVector,
    PassthroughEncoder,
    ConstantEmbeddingClient,
)
from .models import RetrievalRequest, RetrievalResponse

if TYPE_CHECKING:
    from fastapi import APIRouter

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
