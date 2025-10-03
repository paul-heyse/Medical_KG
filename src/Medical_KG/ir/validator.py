from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

try:
    from jsonschema.validators import Draft202012Validator as _Draft202012Validator
except Exception:  # pragma: no cover - fallback for doc builds

    class _Draft202012Validator:  # minimal stub
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def validate(self, instance: Any) -> None:
            return None


from Medical_KG.ir.models import DocumentIR, ensure_monotonic_spans


class ValidationError(Exception):
    pass


class IRValidator:
    def __init__(self) -> None:
        schema_path = Path(__file__).resolve().parent / "schemas" / "document.v1.schema.json"
        self.document_validator = _Draft202012Validator(schema=_load_json(schema_path))

    def _load_schema(self, path: Path) -> Mapping[str, Any]:
        return json.loads(path.read_text())

    def validate_document(self, document: DocumentIR) -> None:
        payload = document.as_dict()
        if not document.doc_id:
            raise ValidationError("Document must have a doc_id")
        if not document.uri:
            raise ValidationError("Document must have a uri")
        try:
            self.document_validator.validate(payload)
        except _JsonSchemaError as exc:
            raise ValidationError(f"Document schema validation failed: {exc.message}") from exc

        for block_payload in payload["blocks"]:
            try:
                self.block_validator.validate(block_payload)
            except _JsonSchemaError as exc:
                raise ValidationError(f"Block validation failed: {exc.message}") from exc

        for table_payload in payload["tables"]:
            try:
                self.table_validator.validate(table_payload)
            except _JsonSchemaError as exc:
                raise ValidationError(f"Table validation failed: {exc.message}") from exc
            if table_payload["end"] < table_payload["start"]:
                raise ValidationError("Table span invalid")

        try:
            ensure_monotonic_spans(document.blocks)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        self._validate_offsets(document)
        self._validate_span_map(payload["span_map"])

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
