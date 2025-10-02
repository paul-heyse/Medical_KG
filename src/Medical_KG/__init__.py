"""Medical_KG package exports."""

from typing import TYPE_CHECKING, Any

from Medical_KG.config.manager import ConfigManager, ConfigError

if TYPE_CHECKING:  # pragma: no cover
    from Medical_KG.app import create_app as _create_app


def create_app(*args: Any, **kwargs: Any):
    from Medical_KG.app import create_app as _factory

    return _factory(*args, **kwargs)


def ping() -> str:
    return "pong"


__all__ = ["create_app", "ConfigManager", "ConfigError", "ping"]
