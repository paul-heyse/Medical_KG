"""Structured logging helpers for the Medical KG service."""

from __future__ import annotations

import logging
import os
import random
from importlib import import_module
from types import ModuleType
from typing import Any, Optional, cast


def _load_jsonlogger() -> Optional[ModuleType]:
    try:  # pragma: no cover - optional dependency
        return import_module("pythonjsonlogger.jsonlogger")
    except ModuleNotFoundError:  # pragma: no cover - fallback to stdlib formatter
        return None


def _get_json_formatter_class(module: ModuleType) -> type[Any]:
    formatter_cls = getattr(module, "JsonFormatter", None)
    if formatter_cls is None:
        raise RuntimeError("python-json-logger is missing JsonFormatter")
    return cast(type[Any], formatter_cls)


jsonlogger = _load_jsonlogger()

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

    def _build_formatter() -> logging.Formatter:
        if jsonlogger is None:
            return logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s %(message)s", datefmt="%Y-%m-%dT%H:%M:%S%z"
            )
        formatter_cls = _get_json_formatter_class(jsonlogger)
        formatter = formatter_cls(
            "%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s %(trace_id)s %(span_id)s",
            rename_fields={"levelname": "level", "asctime": "timestamp"},
        )
        return cast(logging.Formatter, formatter)

    global _configured
    if _configured:
        return
    level = os.getenv("MEDKG_LOG_LEVEL", "INFO").upper()
    sample_rate = float(os.getenv("MEDKG_LOG_SAMPLE_RATE", "1.0"))
    handler = logging.StreamHandler()
    handler.setFormatter(_build_formatter())
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
