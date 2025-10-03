"""Typed helpers for optional tiktoken dependency."""

from __future__ import annotations

import importlib
from typing import Protocol, Sequence, cast


class EncodingProtocol(Protocol):
    def encode(self, text: str) -> Sequence[int]:
        ...


def load_encoding(name: str = "cl100k_base") -> EncodingProtocol | None:
    """Load a tiktoken encoding if the dependency is available."""

    spec = importlib.util.find_spec("tiktoken")
    if spec is None:
        return None
    module = importlib.import_module("tiktoken")
    get_encoding = getattr(module, "get_encoding", None)
    if not callable(get_encoding):
        return None
    encoding = get_encoding(name)
    if hasattr(encoding, "encode"):
        return cast(EncodingProtocol, encoding)
    return None


__all__ = ["EncodingProtocol", "load_encoding"]
