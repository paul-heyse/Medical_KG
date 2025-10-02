"""Medical_KG package exports."""

from typing import Any

from Medical_KG.config.manager import ConfigError, ConfigManager


def create_app(*args: Any, **kwargs: Any):
    from Medical_KG.app import create_app as _factory

    return _factory(*args, **kwargs)


def ping() -> str:
    return "pong"


__all__ = ["ConfigError", "ConfigManager", "create_app", "ping"]
