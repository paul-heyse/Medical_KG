"""Medical_KG package exports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, cast

if TYPE_CHECKING:
    from fastapi import FastAPI
else:  # pragma: no cover - optional FastAPI dependency for runtime imports
    FastAPI = Any  # type: ignore[assignment]

from Medical_KG.config.manager import ConfigError, ConfigManager


def create_app(*args: Any, **kwargs: Any) -> FastAPI:
    from Medical_KG.app import create_app as _factory

    factory = cast(Callable[..., FastAPI], _factory)
    return factory(*args, **kwargs)


def ping() -> str:
    return "pong"


__all__ = ["ConfigError", "ConfigManager", "create_app", "ping"]
