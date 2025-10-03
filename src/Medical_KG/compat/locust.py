"""Typed accessors for the optional locust dependency."""

from __future__ import annotations

import importlib
import importlib.util
from typing import Any, Callable, ParamSpec, Protocol, Tuple, TypeVar, cast

P = ParamSpec("P")
R = TypeVar("R")


class HttpUserProtocol(Protocol):
    wait_time: Callable[..., float]

    def __init__(self, *args: Any, **kwargs: Any) -> None: ...


WaitTimeFactory = Callable[[float, float], Callable[[], float]]
TaskDecorator = Callable[[Callable[P, R]], Callable[P, R]]


def load_locust() -> Tuple[type[HttpUserProtocol], WaitTimeFactory, TaskDecorator] | None:
    """Return locust primitives if the dependency is available."""

    spec = importlib.util.find_spec("locust")
    if spec is None:
        return None
    module = importlib.import_module("locust")
    http_user = getattr(module, "HttpUser", None)
    between = getattr(module, "between", None)
    task = getattr(module, "task", None)
    if http_user is None or between is None or task is None:
        return None
    return (
        cast(type[HttpUserProtocol], http_user),
        cast(WaitTimeFactory, between),
        cast(TaskDecorator, task),
    )


__all__ = ["HttpUserProtocol", "TaskDecorator", "WaitTimeFactory", "load_locust"]
