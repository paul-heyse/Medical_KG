"""Scope-based access control."""
from __future__ import annotations

from typing import Iterable, Sequence


class ScopeError(PermissionError):
    """Raised when a request lacks required scopes."""


class ScopeEnforcer:
    def __init__(self, required_scopes: Sequence[str]) -> None:
        self._required = set(required_scopes)

    def verify(self, provided: Iterable[str]) -> None:
        provided_set = set(provided)
        missing = self._required - provided_set
        if missing:
            raise ScopeError(f"Missing scopes: {', '.join(sorted(missing))}")


__all__ = ["ScopeEnforcer", "ScopeError"]
