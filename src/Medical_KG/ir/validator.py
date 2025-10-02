from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

try:  # pragma: no cover - optional dependency
    from jsonschema import Draft202012Validator, ValidationError as _JsonSchemaError
except ModuleNotFoundError:  # pragma: no cover - fallback for lightweight environments
    class _JsonSchemaError(Exception):
        def __init__(self, message: str) -> None:
            super().__init__(message)
            self.message = message

    class Draft202012Validator:  # type: ignore[override]
        def __init__(self, schema: Mapping[str, Any]) -> None:
            self.schema = schema

        def validate(self, instance: Mapping[str, Any]) -> None:
            required = self.schema.get("required", [])
            for field in required:
                if field not in instance:
                    raise _JsonSchemaError(f"Missing required field '{field}'")

from Medical_KG.ir.models import DocumentIR, ensure_monotonic_spans


class ValidationError(Exception):
    pass


class IRValidator:
    def __init__(self, *, schema_dir: Path | None = None) -> None:
        base = schema_dir or Path(__file__).resolve().parent / "schemas"
        self.document_schema = self._load_schema(base / "document.schema.json")
        self.block_schema = self._load_schema(base / "block.schema.json")
        self.table_schema = self._load_schema(base / "table.schema.json")
        self.document_validator = Draft202012Validator(self.document_schema)
        self.block_validator = Draft202012Validator(self.block_schema)
        self.table_validator = Draft202012Validator(self.table_schema)

    def _load_schema(self, path: Path) -> Mapping[str, Any]:
        return json.loads(path.read_text())

    def validate_document(self, document: DocumentIR) -> None:
        payload = document.as_dict()
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

        try:
            ensure_monotonic_spans(document.blocks)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        self._validate_offsets(document)

    def _validate_offsets(self, document: DocumentIR) -> None:
        text_length = len(document.text)
        for block in document.blocks:
            if block.end > text_length:
                raise ValidationError("Block span exceeds document length")
        for table in document.tables:
            if table.end < table.start:
                raise ValidationError("Table span invalid")
