from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Sequence


@dataclass(slots=True)
class Span:
    raw_start: int
    raw_end: int
    canonical_start: int
    canonical_end: int
    transform: str
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None


@dataclass(slots=True)
class SpanMap:
    spans: List[Span] = field(default_factory=list)

    def add(
        self,
        raw_start: int,
        raw_end: int,
        canonical_start: int,
        canonical_end: int,
        transform: str,
        *,
        page: int | None = None,
        bbox: Iterable[float] | None = None,
    ) -> None:
        bbox_tuple: tuple[float, float, float, float] | None = None
        if bbox is not None:
            values = tuple(float(value) for value in bbox)
            if len(values) != 4:
                raise ValueError("bbox must contain four coordinates")
            bbox_tuple = tuple(float(coord) for coord in values)
        self.spans.append(
            Span(
                raw_start,
                raw_end,
                canonical_start,
                canonical_end,
                transform,
                page=page,
                bbox=bbox_tuple,
            )
        )

    def to_list(self) -> List[Dict[str, Any]]:
        result: List[Dict[str, Any]] = []
        for span in self.spans:
            entry: Dict[str, Any] = {
                "raw_start": span.raw_start,
                "raw_end": span.raw_end,
                "canonical_start": span.canonical_start,
                "canonical_end": span.canonical_end,
                "transform": span.transform,
            }
            if span.page is not None:
                entry["page"] = span.page
            if span.bbox is not None:
                entry["bbox"] = list(span.bbox)
            result.append(entry)
        return result

    def extend_from_offset_map(
        self,
        entries: Iterable[Mapping[str, Any]],
        *,
        transform: str = "offset_map",
    ) -> None:
        new_spans: list[Span] = []
        for entry in entries:
            raw_start = int(entry.get("char_start", entry.get("raw_start", 0)))
            raw_end = int(entry.get("char_end", entry.get("raw_end", 0)))
            canonical_start = int(entry.get("canonical_start", raw_start))
            canonical_end = int(entry.get("canonical_end", raw_end))
            page = entry.get("page")
            bbox = entry.get("bbox") or entry.get("bounding_box")
            bbox_tuple: tuple[float, float, float, float] | None = None
            if bbox is not None:
                values = tuple(float(value) for value in bbox)
                if len(values) != 4:
                    raise ValueError("bbox must contain four coordinates")
                bbox_tuple = tuple(float(coord) for coord in values)
            new_spans.append(
                Span(
                    raw_start,
                    raw_end,
                    canonical_start,
                    canonical_end,
                    transform,
                    page=int(page) if page is not None else None,
                    bbox=bbox_tuple,
                )
            )
        if new_spans:
            existing = [span for span in self.spans if span.transform != "normalize"]
            self.spans = sorted(new_spans + existing, key=lambda span: span.canonical_start)


@dataclass(slots=True)
class Block:
    type: str
    text: str
    start: int
    end: int
    section: str | None = None
    meta: MutableMapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class Table:
    caption: str
    headers: List[str]
    rows: List[List[str]]
    start: int
    end: int
    meta: MutableMapping[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DocumentIR:
    doc_id: str
    source: str
    uri: str
    language: str
    text: str
    raw_text: str
    blocks: List[Block] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)
    span_map: SpanMap = field(default_factory=SpanMap)
    created_at: datetime = field(default_factory=datetime.utcnow)
    provenance: MutableMapping[str, Any] = field(default_factory=dict)

    def add_block(self, block: Block) -> None:
        self.blocks.append(block)

    def add_table(self, table: Table) -> None:
        self.tables.append(table)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "source": self.source,
            "uri": self.uri,
            "language": self.language,
            "text": self.text,
            "raw_text": self.raw_text,
            "blocks": [
                {
                    "type": block.type,
                    "text": block.text,
                    "start": block.start,
                    "end": block.end,
                    "section": block.section,
                    "meta": dict(block.meta),
                }
                for block in self.blocks
            ],
            "tables": [
                {
                    "caption": table.caption,
                    "headers": table.headers,
                    "rows": table.rows,
                    "start": table.start,
                    "end": table.end,
                    "meta": dict(table.meta),
                }
                for table in self.tables
            ],
            "span_map": self.span_map.to_list(),
            "created_at": self.created_at.isoformat(),
            "provenance": dict(self.provenance),
        }


def ensure_monotonic_spans(blocks: Sequence[Block]) -> None:
    previous_end = -1
    for block in blocks:
        if block.start < previous_end:
            raise ValueError("Block spans must be monotonic")
        if block.start > block.end:
            raise ValueError("Invalid block span offsets")
        previous_end = block.end
