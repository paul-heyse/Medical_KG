from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, cast

from Medical_KG.ir.models import DocumentIR, ensure_monotonic_spans


class ValidationError(Exception):
    pass


class IRValidator:
    """Validate :class:`DocumentIR` instances using bundled JSON schemas."""

    def __init__(self, *, schema_dir: Path | None = None) -> None:
        base_dir = schema_dir or Path(__file__).resolve().parent / "schemas"
        self._schema_dir = base_dir
        self._schemas = {
            "document": self._load_schema(base_dir / "document.schema.json"),
            "block": self._load_schema(base_dir / "block.schema.json"),
            "table": self._load_schema(base_dir / "table.schema.json"),
        }
        language_pattern = self._schemas["document"]["properties"]["language"].get("pattern", "")
        self._language_pattern = re.compile(language_pattern) if language_pattern else None

    @property
    def schema_store(self) -> Mapping[str, Mapping[str, Any]]:
        """Expose loaded schemas for tests and tooling."""

        return dict(self._schemas)

    def _load_schema(self, path: Path) -> Mapping[str, Any]:
        result: Any = json.loads(path.read_text(encoding="utf-8"))
        return cast(Mapping[str, Any], result)

    def validate_document(self, document: DocumentIR) -> None:
        payload = document.as_dict()
        if not document.doc_id:
            raise ValidationError("Document must have a doc_id")
        if not document.uri:
            raise ValidationError("Document must have a uri")

        self._validate_document_payload(payload)

        for block_payload in payload["blocks"]:
            self._validate_block_payload(block_payload)

        for table_payload in payload["tables"]:
            self._validate_table_payload(table_payload)

        try:
            ensure_monotonic_spans(document.blocks)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        self._validate_offsets(document)
        self._validate_span_map(payload["span_map"])

    def _validate_document_payload(self, payload: Mapping[str, Any]) -> None:
        schema = self._schemas["document"]
        required = schema.get("required", [])
        missing = [field for field in required if field not in payload]
        if missing:
            raise ValidationError(f"Document missing required fields: {', '.join(missing)}")

        for field in ("doc_id", "source", "uri", "language", "text", "raw_text"):
            value = payload.get(field)
            if not isinstance(value, str):
                raise ValidationError(f"Document field '{field}' must be a string")
            if field in {"doc_id", "source", "uri"} and not value.strip():
                raise ValidationError(f"Document field '{field}' cannot be empty")

        if self._language_pattern and not self._language_pattern.fullmatch(payload["language"]):
            raise ValidationError("Document language must be a two-letter code")

        if not isinstance(payload.get("blocks"), list):
            raise ValidationError("Document blocks must be an array")
        if not isinstance(payload.get("tables"), list):
            raise ValidationError("Document tables must be an array")
        if not isinstance(payload.get("span_map"), list):
            raise ValidationError("Document span_map must be an array")

        provenance = payload.get("provenance", {})
        if provenance is not None and not isinstance(provenance, dict):
            raise ValidationError("Document provenance must be an object")

        allowed_keys = set(schema.get("properties", {}).keys()) | {"created_at"}
        extras = set(payload.keys()) - allowed_keys
        if extras:
            raise ValidationError(f"Document contains unsupported fields: {', '.join(sorted(extras))}")

    def _validate_block_payload(self, block: Mapping[str, Any]) -> None:
        schema = self._schemas["block"]
        required = schema.get("required", [])
        missing = [field for field in required if field not in block]
        if missing:
            raise ValidationError(f"Block missing required fields: {', '.join(missing)}")

        allowed_keys = set(schema.get("properties", {}).keys())
        extras = set(block.keys()) - allowed_keys
        if extras:
            raise ValidationError(f"Block contains unsupported fields: {', '.join(sorted(extras))}")

        if not isinstance(block["type"], str) or not block["type"]:
            raise ValidationError("Block type must be a non-empty string")
        if not isinstance(block["text"], str):
            raise ValidationError("Block text must be a string")
        for field in ("start", "end"):
            value = block[field]
            if not isinstance(value, int) or value < 0:
                raise ValidationError(f"Block {field} must be a non-negative integer")

        section = block.get("section")
        if section is not None and not isinstance(section, str):
            raise ValidationError("Block section must be a string or None")

        meta = block.get("meta", {})
        if not isinstance(meta, dict):
            raise ValidationError("Block meta must be an object")

    def _validate_table_payload(self, table: Mapping[str, Any]) -> None:
        schema = self._schemas["table"]
        required = schema.get("required", [])
        missing = [field for field in required if field not in table]
        if missing:
            raise ValidationError(f"Table missing required fields: {', '.join(missing)}")

        allowed_keys = set(schema.get("properties", {}).keys())
        extras = set(table.keys()) - allowed_keys
        if extras:
            raise ValidationError(f"Table contains unsupported fields: {', '.join(sorted(extras))}")

        if not isinstance(table["caption"], str):
            raise ValidationError("Table caption must be a string")
        if not isinstance(table.get("headers"), list):
            raise ValidationError("Table headers must be an array")
        if not all(isinstance(header, str) for header in table["headers"]):
            raise ValidationError("Table headers must be strings")
        if not isinstance(table.get("rows"), list):
            raise ValidationError("Table rows must be an array")
        for row in table["rows"]:
            if not isinstance(row, list) or not all(isinstance(cell, str) for cell in row):
                raise ValidationError("Table rows must be arrays of strings")

        for field in ("start", "end"):
            value = table[field]
            if not isinstance(value, int) or value < 0:
                raise ValidationError(f"Table {field} must be a non-negative integer")
        if table["end"] < table["start"]:
            raise ValidationError("Table span invalid")

        meta = table.get("meta", {})
        if not isinstance(meta, dict):
            raise ValidationError("Table meta must be an object")

    def _validate_offsets(self, document: DocumentIR) -> None:
        text_length = len(document.text)
        for block in document.blocks:
            if block.end > text_length:
                raise ValidationError("Block span exceeds document length")
            if block.section is not None and not isinstance(block.section, str):
                raise ValidationError("Block section must be a string or None")

    def _validate_span_map(self, span_map: list[Mapping[str, Any]]) -> None:
        previous_end = 0
        for entry in span_map:
            canonical_start = entry["canonical_start"]
            canonical_end = entry["canonical_end"]
            if canonical_start > canonical_end:
                raise ValidationError("Span map canonical offsets invalid")
            if canonical_start < previous_end:
                raise ValidationError("Span map must be monotonic")
            if "page" in entry and entry["page"] is not None and entry["page"] < 1:
                raise ValidationError("Span map page numbers must be >= 1")
            previous_end = canonical_end
