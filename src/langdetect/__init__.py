from __future__ import annotations

import re

_ASCII_RE = re.compile(r"^[\x00-\x7F]+$")


def detect(text: str) -> str:
    if not text:
        return "unknown"
    if _ASCII_RE.match(text):
        return "en"
    return "unknown"
