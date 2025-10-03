"""Token counting utilities using tiktoken with graceful fallback."""

from __future__ import annotations

from functools import lru_cache

from Medical_KG.compat import EncodingProtocol, load_encoding


@lru_cache(maxsize=1)
def _encoding() -> EncodingProtocol | None:
    try:
        return load_encoding("cl100k_base")
    except Exception:  # pragma: no cover - fallback path
        return None


def count_tokens(text: str) -> int:
    """Return token length using Qwen-compatible tokenizer fallback."""

    encoding = _encoding()
    if encoding is None:
        return len(text.split())
    return len(encoding.encode(text))
