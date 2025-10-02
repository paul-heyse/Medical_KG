from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, MutableMapping, Sequence


@dataclass(slots=True)
class Span:
    raw_start: int
    raw_end: int
    canonical_start: int
    canonical_end: int
    transform: str


@dataclass(slots=True)
class SpanMap:
    spans: List[Span] = field(default_factory=list)

    def add(self, raw_start: int, raw_end: int, canonical_start: int, canonical_end: int, transform: str) -> None:
        self.spans.append(Span(raw_start, raw_end, canonical_start, canonical_end, transform))

    def to_list(self) -> List[Dict[str, Any]]:
        return [
            {
                "raw_start": span.raw_start,
                "raw_end": span.raw_end,
                "canonical_start": span.canonical_start,
                "canonical_end": span.canonical_end,
                "transform": span.transform,
            }
            for span in self.spans
        ]


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
