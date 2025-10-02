"""Minimal YAML shim backed by JSON parsing."""
from __future__ import annotations

import json
from typing import Any, IO


def safe_load(stream: Any) -> Any:
    if hasattr(stream, "read"):
        text = stream.read()
    else:
        text = stream
    if text is None or text == "":
        return {}
    return json.loads(text)
