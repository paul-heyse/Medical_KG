"""Structured logging helpers for the Medical KG service."""

from __future__ import annotations

import logging
import os
import random
from typing import Any

try:  # pragma: no cover - optional dependency
    from pythonjsonlogger import jsonlogger
except ModuleNotFoundError:  # pragma: no cover - fallback to stdlib formatter
    jsonlogger = None

__all__ = ["configure_logging"]


class SamplingFilter(logging.Filter):
    """Probabilistic log sampling filter."""

    def __init__(self, rate: float) -> None:
        super().__init__()
        self._rate = max(0.0, min(rate, 1.0))

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        if self._rate >= 1.0:
            return True
        return random.random() < self._rate


_configured = False


def configure_logging(extra_fields: dict[str, Any] | None = None) -> None:
    """Configure application-wide JSON logging with sampling support."""

    global _configured
    if _configured:
        return
    level = os.getenv("MEDKG_LOG_LEVEL", "INFO").upper()
    sample_rate = float(os.getenv("MEDKG_LOG_SAMPLE_RATE", "1.0"))
    handler = logging.StreamHandler()
    if jsonlogger is not None:
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(trace_id)s %(span_id)s",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z"
        )
    handler.setFormatter(formatter)
    handler.addFilter(SamplingFilter(sample_rate))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    if extra_fields:
        logging.LoggerAdapter(logging.getLogger("medkg.context"), extra_fields).debug(
            "Logging context initialised", extra=extra_fields
        )
    _configured = True
