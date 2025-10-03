"""Token counting utilities using tiktoken with graceful fallback."""
from __future__ import annotations

import importlib
from functools import lru_cache
from typing import Optional

tiktoken_spec = importlib.util.find_spec("tiktoken")
if tiktoken_spec is not None:
    tiktoken = importlib.import_module("tiktoken")
else:  # pragma: no cover - optional dependency
    tiktoken = None


@lru_cache(maxsize=1)
def _encoding() -> Optional["tiktoken.Encoding"]:
    if tiktoken is None:
        return None
    try:
        return tiktoken.get_encoding("cl100k_base")
    except Exception:  # pragma: no cover - fallback path
        return None


def count_tokens(text: str) -> int:
    """Return token length using Qwen-compatible tokenizer fallback."""

    encoding = _encoding()
    if encoding is None:
        return len(text.split())
    return len(encoding.encode(text))
