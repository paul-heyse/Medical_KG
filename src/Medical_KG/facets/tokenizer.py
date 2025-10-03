"""Token counting utilities using tiktoken with graceful fallback."""
from __future__ import annotations

from functools import lru_cache
from typing import Optional

from Medical_KG.utils.optional_dependencies import TokenEncoder, get_tiktoken_encoding


@lru_cache(maxsize=1)
def _encoding() -> Optional[TokenEncoder]:
    return get_tiktoken_encoding()


def count_tokens(text: str) -> int:
    """Return token length using Qwen-compatible tokenizer fallback."""

    encoding = _encoding()
    if encoding is None:
        return len(text.split())
    return len(encoding.encode(text))
