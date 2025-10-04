"""Retrieval orchestration package."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, NoReturn, cast

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

from Medical_KG.utils.optional_dependencies import MissingDependencyError, optional_import

if TYPE_CHECKING:
    from .api import create_router
else:  # pragma: no cover - optional FastAPI dependency
    try:
        _api_module = optional_import(
            "Medical_KG.retrieval.api",
            feature_name="fastapi",
            package_name="fastapi",
        )
    except MissingDependencyError:

        def create_router(service: RetrievalService) -> NoReturn:  # pragma: no cover - fallback
            raise RuntimeError("FastAPI integration is unavailable: fastapi not installed")

    else:
        create_router = cast(Callable[[RetrievalService], Any], getattr(_api_module, "create_router"))


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
