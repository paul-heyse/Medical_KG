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
    """Validate external JSON payloads that should be objects.

    These helpers are intended for HTTP boundary parsing where upstream APIs may
    drift; internal adapter code should rely on TypedDict guarantees instead of
    re-validating structures.
    """

    if not isinstance(value, Mapping):
        raise TypeError(f"{context} expected a mapping, received {type(value).__name__}")
    return value


def ensure_json_sequence(value: JSONValue, *, context: str) -> JSONSequence:
    """Validate external JSON payloads that should be arrays or sequences.

    Restrict usage to adapter fetch methods so downstream code can assume TypedDict
    fields already honour their declared sequence types.
    """

    if not isinstance(value, Sequence):
        raise TypeError(f"{context} expected a sequence, received {type(value).__name__}")
    return value


def ensure_json_value(value: object, *, context: str) -> JSONValue:
    """Coerce arbitrary external JSON into a :class:`JSONValue`.

    Use this helper when parsing HTTP responses so API schema changes surface as
    type errors; avoid calling it inside TypedDict-backed parse methods.
    """

    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, Mapping):
        return {
            str(key): ensure_json_value(item, context=f"{context} mapping value")
            for key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [ensure_json_value(item, context=f"{context} sequence item") for item in value]
    raise TypeError(
        f"{context} expected a JSON-serializable value, received {type(value).__name__}"
    )
