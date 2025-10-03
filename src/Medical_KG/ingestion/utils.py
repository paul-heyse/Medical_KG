from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Mapping, Sequence

from langdetect import detect

from Medical_KG.ingestion.types import JSONMapping, JSONSequence, JSONValue

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


def canonical_json(data: Mapping[str, object]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def ensure_json_mapping(value: JSONValue, *, context: str) -> JSONMapping:
    if not isinstance(value, Mapping):
        raise TypeError(f"{context} expected a mapping, received {type(value).__name__}")
    return value


def ensure_json_sequence(value: JSONValue, *, context: str) -> JSONSequence:
    if not isinstance(value, Sequence):
        raise TypeError(f"{context} expected a sequence, received {type(value).__name__}")
    return value
