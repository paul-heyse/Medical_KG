"""Ingestion subsystem for external data sources."""

from .http_client import AsyncHttpClient
from .ledger import IngestionLedger
from .models import Document, IngestionResult
from .registry import available_sources, get_adapter

__all__ = [
    "AsyncHttpClient",
    "IngestionLedger",
    "Document",
    "IngestionResult",
    "available_sources",
    "get_adapter",
]
