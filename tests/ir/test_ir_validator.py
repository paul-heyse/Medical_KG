from __future__ import annotations

import pytest

from Medical_KG.ir.models import Block, DocumentIR, SpanMap, Table
from Medical_KG.ir.validator import IRValidator, ValidationError


def _make_document() -> DocumentIR:
    document = DocumentIR(
        doc_id="doc-1",
        source="unit-test",
        uri="https://example/doc-1",
        language="en",
        text="Heading\n\nContent",
        raw_text="Heading\n\nContent",
    )
    document.add_block(
        Block(type="heading", text="Heading", start=0, end=7, section="title", meta={})
    )
    document.add_block(
        Block(type="paragraph", text="Content", start=9, end=16, section="body", meta={})
    )
    document.add_table(
        Table(caption="Table 1", headers=["h1"], rows=[["r1"]], start=16, end=23, meta={})
    )
    document.span_map = SpanMap()
    document.span_map.add(0, len(document.raw_text), 0, len(document.text), "normalize", page=1)
    document.provenance["source"] = "fixture"
    return document


def test_ir_validator_accepts_valid_document() -> None:
    validator = IRValidator()
    validator.validate_document(_make_document())
    assert "document" in validator.schema_store


def test_ir_validator_requires_doc_id() -> None:
    document = _make_document()
    document.doc_id = ""
    with pytest.raises(ValidationError, match="doc_id"):
        IRValidator().validate_document(document)


def test_ir_validator_requires_uri() -> None:
    document = _make_document()
    document.uri = ""
    with pytest.raises(ValidationError, match="uri"):
        IRValidator().validate_document(document)


def test_ir_validator_enforces_language_pattern() -> None:
    document = _make_document()
    document.language = "english"
    with pytest.raises(ValidationError, match="language"):
        IRValidator().validate_document(document)


def test_ir_validator_rejects_extra_document_fields() -> None:
    validator = IRValidator()
    payload = _make_document().as_dict()
    payload["unexpected"] = "value"
    with pytest.raises(ValidationError, match="unsupported"):
        validator._validate_document_payload(payload)  # type: ignore[arg-type]


def test_ir_validator_rejects_invalid_block_payload() -> None:
    validator = IRValidator()
    block_payload = {
        "type": "heading",
        "text": "Title",
        "start": 0,
        "end": 5,
        "meta": {},
        "section": None,
        "extra": True,
    }
    with pytest.raises(ValidationError, match="unsupported"):
        validator._validate_block_payload(block_payload)


def test_ir_validator_rejects_block_meta_type() -> None:
    validator = IRValidator()
    block_payload = {
        "type": "heading",
        "text": "Title",
        "start": 0,
        "end": 5,
        "meta": "invalid",
    }
    with pytest.raises(ValidationError, match="meta"):
        validator._validate_block_payload(block_payload)


def test_ir_validator_rejects_table_payload_errors() -> None:
    validator = IRValidator()
    table_payload = {
        "caption": "T",
        "headers": ["h"],
        "rows": [["r"]],
        "start": 2,
        "end": 1,
    }
    with pytest.raises(ValidationError, match="span"):
        validator._validate_table_payload(table_payload)


def test_ir_validator_table_requires_string_rows() -> None:
    validator = IRValidator()
    table_payload = {
        "caption": "T",
        "headers": ["h"],
        "rows": [[1]],
        "start": 0,
        "end": 0,
        "meta": {},
    }
    with pytest.raises(ValidationError, match="rows"):
        validator._validate_table_payload(table_payload)


def test_ir_validator_rejects_table_meta_type() -> None:
    validator = IRValidator()
    table_payload = {
        "caption": "T",
        "headers": ["h"],
        "rows": [["r"]],
        "start": 0,
        "end": 0,
        "meta": "invalid",
    }
    with pytest.raises(ValidationError, match="meta"):
        validator._validate_table_payload(table_payload)


def test_ir_validator_rejects_span_map_page_floor() -> None:
    document = _make_document()
    end = len(document.text)
    document.span_map.add(end, end + 1, end, end + 1, "normalize", page=0)
    with pytest.raises(ValidationError, match="page numbers"):
        IRValidator().validate_document(document)


def test_ir_validator_rejects_block_offset_overflow() -> None:
    document = _make_document()
    overflow = len(document.text) + 5
    document.blocks[0].end = overflow
    document.blocks[1].start = overflow
    document.blocks[1].end = overflow + 1
    with pytest.raises(ValidationError, match="exceeds"):
        IRValidator().validate_document(document)


def test_ir_validator_document_missing_required_field() -> None:
    validator = IRValidator()
    payload = _make_document().as_dict()
    payload.pop("doc_id")
    with pytest.raises(ValidationError, match="missing required"):
        validator._validate_document_payload(payload)  # type: ignore[arg-type]


def test_ir_validator_document_field_type() -> None:
    validator = IRValidator()
    payload = _make_document().as_dict()
    payload["doc_id"] = 123  # type: ignore[assignment]
    with pytest.raises(ValidationError, match="must be a string"):
        validator._validate_document_payload(payload)  # type: ignore[arg-type]


def test_ir_validator_document_collections_must_be_lists() -> None:
    validator = IRValidator()
    payload = _make_document().as_dict()
    payload["blocks"] = "invalid"
    with pytest.raises(ValidationError, match="blocks must be an array"):
        validator._validate_document_payload(payload)  # type: ignore[arg-type]
    payload["blocks"] = []
    payload["tables"] = "invalid"
    with pytest.raises(ValidationError, match="tables must be an array"):
        validator._validate_document_payload(payload)  # type: ignore[arg-type]
    payload["tables"] = []
    payload["span_map"] = "invalid"
    with pytest.raises(ValidationError, match="span_map must be an array"):
        validator._validate_document_payload(payload)  # type: ignore[arg-type]


def test_ir_validator_document_provenance_type() -> None:
    validator = IRValidator()
    payload = _make_document().as_dict()
    payload["provenance"] = "invalid"
    with pytest.raises(ValidationError, match="provenance"):
        validator._validate_document_payload(payload)  # type: ignore[arg-type]


def test_ir_validator_block_missing_fields() -> None:
    validator = IRValidator()
    block_payload = {"type": "heading", "start": 0, "end": 5}
    with pytest.raises(ValidationError, match="missing required"):
        validator._validate_block_payload(block_payload)


def test_ir_validator_block_type_and_text_validation() -> None:
    validator = IRValidator()
    block_payload = {
        "type": "",
        "text": "Title",
        "start": 0,
        "end": 1,
        "meta": {},
    }
    with pytest.raises(ValidationError, match="non-empty"):
        validator._validate_block_payload(block_payload)
    block_payload["type"] = "heading"
    block_payload["text"] = 123  # type: ignore[assignment]
    with pytest.raises(ValidationError, match="text must be a string"):
        validator._validate_block_payload(block_payload)


def test_ir_validator_block_offset_types() -> None:
    validator = IRValidator()
    block_payload = {
        "type": "heading",
        "text": "Title",
        "start": -1,
        "end": 1,
        "meta": {},
    }
    with pytest.raises(ValidationError, match="start must be a non-negative integer"):
        validator._validate_block_payload(block_payload)
    block_payload["start"] = 0
    block_payload["end"] = "1"  # type: ignore[assignment]
    with pytest.raises(ValidationError, match="end must be a non-negative integer"):
        validator._validate_block_payload(block_payload)


def test_ir_validator_block_section_type_guard() -> None:
    validator = IRValidator()
    block_payload = {
        "type": "heading",
        "text": "Title",
        "start": 0,
        "end": 1,
        "meta": {},
        "section": 123,
    }
    with pytest.raises(ValidationError, match="section must be a string"):
        validator._validate_block_payload(block_payload)


def test_ir_validator_offsets_section_guard() -> None:
    document = _make_document()
    document.blocks[0].section = 123  # type: ignore[assignment]
    with pytest.raises(ValidationError, match="section must be a string"):
        IRValidator()._validate_offsets(document)


def test_ir_validator_table_missing_fields() -> None:
    validator = IRValidator()
    table_payload = {"caption": "T", "headers": ["h"], "start": 0, "end": 0}
    with pytest.raises(ValidationError, match="missing required"):
        validator._validate_table_payload(table_payload)


def test_ir_validator_table_extra_fields() -> None:
    validator = IRValidator()
    table_payload = {
        "caption": "T",
        "headers": ["h"],
        "rows": [["r"]],
        "start": 0,
        "end": 0,
        "meta": {},
        "extra": True,
    }
    with pytest.raises(ValidationError, match="unsupported"):
        validator._validate_table_payload(table_payload)


def test_ir_validator_table_header_and_row_types() -> None:
    validator = IRValidator()
    table_payload = {
        "caption": 1,
        "headers": ["h"],
        "rows": [["r"]],
        "start": 0,
        "end": 0,
        "meta": {},
    }
    with pytest.raises(ValidationError, match="caption"):
        validator._validate_table_payload(table_payload)
    table_payload["caption"] = "T"
    table_payload["headers"] = "h"  # type: ignore[assignment]
    with pytest.raises(ValidationError, match="headers must be an array"):
        validator._validate_table_payload(table_payload)
    table_payload["headers"] = [123]  # type: ignore[list-item]
    with pytest.raises(ValidationError, match="headers must be strings"):
        validator._validate_table_payload(table_payload)


def test_ir_validator_table_row_collection_types() -> None:
    validator = IRValidator()
    table_payload = {
        "caption": "T",
        "headers": ["h"],
        "rows": "invalid",
        "start": 0,
        "end": 0,
        "meta": {},
    }
    with pytest.raises(ValidationError, match="rows must be an array"):
        validator._validate_table_payload(table_payload)
    table_payload["rows"] = [[1]]
    with pytest.raises(ValidationError, match="rows must be arrays of strings"):
        validator._validate_table_payload(table_payload)


def test_ir_validator_table_offset_types() -> None:
    validator = IRValidator()
    table_payload = {
        "caption": "T",
        "headers": ["h"],
        "rows": [["r"]],
        "start": -1,
        "end": 0,
        "meta": {},
    }
    with pytest.raises(ValidationError, match="start must be a non-negative integer"):
        validator._validate_table_payload(table_payload)
    table_payload["start"] = 0
    table_payload["end"] = "0"  # type: ignore[assignment]
    with pytest.raises(ValidationError, match="end must be a non-negative integer"):
        validator._validate_table_payload(table_payload)


def test_ir_validator_span_map_monotonicity() -> None:
    validator = IRValidator()
    span_map = [
        {"canonical_start": 0, "canonical_end": 5},
        {"canonical_start": 3, "canonical_end": 7},
    ]
    with pytest.raises(ValidationError, match="monotonic"):
        validator._validate_span_map(span_map)  # type: ignore[arg-type]


