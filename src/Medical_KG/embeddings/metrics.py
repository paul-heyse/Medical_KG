"""Prometheus metrics for embedding service operations."""

from __future__ import annotations

from Medical_KG.compat.prometheus import Counter, Histogram

EMBEDDING_REQUESTS = Counter(
    "embedding_requests_total",
    "Total number of embedding batches processed",
    ["model", "device"],
)

EMBEDDING_ERRORS = Counter(
    "embedding_request_errors_total",
    "Total number of embedding failures",
    ["model", "device"],
)

EMBEDDING_LATENCY = Histogram(
    "embedding_request_latency_seconds",
    "Latency of embedding requests",
    ["model", "device"],
)

__all__ = [
    "EMBEDDING_ERRORS",
    "EMBEDDING_LATENCY",
    "EMBEDDING_REQUESTS",
]
