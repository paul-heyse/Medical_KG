"""Document structures used for semantic chunking."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(slots=True)
class Section:
    name: str
    start: int
    end: int
    loinc_code: Optional[str] = None


@dataclass(slots=True)
class Table:
    html: str
    digest: str
    start: int
    end: int


@dataclass(slots=True)
class Document:
    doc_id: str
    text: str
    sections: List[Section] = field(default_factory=list)
    tables: List[Table] = field(default_factory=list)
    source_system: Optional[str] = None
    media_type: Optional[str] = None

    def section_for_offset(self, offset: int) -> Optional[Section]:
        for section in self.sections:
            if section.start <= offset < section.end:
                return section
        return None

    def iter_tables(self) -> List[Table]:
        return self.tables


__all__ = ["Document", "Section", "Table"]
