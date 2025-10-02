"""Ingestion subsystem for external data sources."""

from .http_client import AsyncHttpClient
from .ledger import IngestionLedger
from .models import Document, IngestionResult

__all__ = [
    "AsyncHttpClient",
    "IngestionLedger",
    "Document",
    "IngestionResult",
]
