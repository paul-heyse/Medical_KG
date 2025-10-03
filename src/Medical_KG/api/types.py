"""Shared typing helpers for the API layer."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, TypeAlias, TypeVar

T = TypeVar("T")

# FastAPI dependencies accept arbitrary parameters injected via Depends/Header/etc.
DependencyCallable = Callable[..., Awaitable[T]]

# The application returned by ``create_app`` exposes a FastAPI-compatible interface.
FastAPIApp: TypeAlias = Any

__all__ = ["DependencyCallable", "FastAPIApp", "T"]
