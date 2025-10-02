from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any, Mapping

from langdetect import detect


LANGUAGE_PATTERN = re.compile(r"^[a-z]{2}")


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def detect_language(value: str) -> str:
    try:
        language = detect(value)
    except Exception:  # pragma: no cover - upstream library raises generic exceptions
        return "unknown"
    match = LANGUAGE_PATTERN.match(language)
    return match.group(0) if match else language


def hash_content(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def generate_doc_id(source: str, identifier: str, version: str, content: bytes) -> str:
    digest = hash_content(content)[:12]
    return f"{source}:{identifier}#{version}:{digest}"


def canonical_json(data: Mapping[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
