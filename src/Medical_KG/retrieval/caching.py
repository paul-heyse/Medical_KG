"""TTL cache utilities used by retrieval components."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Callable, Dict, Generic, Hashable, Protocol, TypeVar

T = TypeVar("T")


@dataclass(slots=True)
class _Entry(Generic[T]):
    value: T
    expires_at: datetime


class CacheProtocol(Protocol[T]):
    """Typed interface for cache implementations used by retrieval."""

    def get_or_set(self, key: Hashable, factory: Callable[[], T]) -> T:
        ...

    def get(self, key: Hashable) -> T | None:
        ...

    def set(self, key: Hashable, value: T) -> None:
        ...

    def invalidate(self, key: Hashable) -> None:
        ...

    def clear(self) -> None:
        ...


class TTLCache(Generic[T]):
    """Minimal thread-safe TTL cache with explicit invalidation."""

    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._data: Dict[Hashable, _Entry[T]] = {}
        self._lock = Lock()

    def get_or_set(self, key: Hashable, factory: Callable[[], T]) -> T:
        now = datetime.now(timezone.utc)
        with self._lock:
            entry = self._data.get(key)
            if entry and entry.expires_at > now:
                return entry.value
        value = factory()
        expires_at = now + timedelta(seconds=self._ttl)
        with self._lock:
            self._data[key] = _Entry(value=value, expires_at=expires_at)
        return value

    def get(self, key: Hashable) -> T | None:
        now = datetime.now(timezone.utc)
        with self._lock:
            entry = self._data.get(key)
            if entry and entry.expires_at > now:
                return entry.value
            if entry:
                del self._data[key]
        return None

    def set(self, key: Hashable, value: T) -> None:
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=self._ttl)
        with self._lock:
            self._data[key] = _Entry(value=value, expires_at=expires_at)

    def invalidate(self, key: Hashable) -> None:
        with self._lock:
            self._data.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


__all__ = ["TTLCache", "CacheProtocol"]
