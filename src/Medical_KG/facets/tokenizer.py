"""Token counting utilities using tiktoken with graceful fallback."""
from __future__ import annotations

from functools import lru_cache

try:
    import tiktoken
except Exception:  # pragma: no cover - library not available during some tests
    tiktoken = None  # type: ignore[assignment]


@lru_cache(maxsize=1)
def _encoding() -> "tiktoken.Encoding | None":  # type: ignore[name-defined]
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
