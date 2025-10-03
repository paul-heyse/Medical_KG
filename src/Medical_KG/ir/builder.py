from __future__ import annotations

from collections.abc import Mapping, Sequence
from html.parser import HTMLParser
from typing import Any, List, Tuple

try:  # pragma: no cover - optional dependency
    from bs4 import BeautifulSoup
except ModuleNotFoundError:  # pragma: no cover - fallback to stdlib parser
    BeautifulSoup = None

from Medical_KG.ir.models import Block, DocumentIR, SpanMap, Table
from Medical_KG.ir.normalizer import TextNormalizer, section_from_heading


class IrBuilder:
    """Base builder converting source payloads into IR objects."""

    def __init__(self, *, normalizer: TextNormalizer | None = None) -> None:
        self.normalizer = normalizer or TextNormalizer()

    def build(
        self,
        *,
        doc_id: str,
        source: str,
        uri: str,
        text: str,
        metadata: Mapping[str, Any] | None = None,
    ) -> DocumentIR:
        metadata = metadata or {}
        normalized = self.normalizer.normalize(text)
        document = DocumentIR(
            doc_id=doc_id,
            source=source,
            uri=uri,
            language=normalized.language,
            text=normalized.text,
            raw_text=normalized.raw_text,
        )
        document.span_map = SpanMap()
        span_entries = metadata.get("span_map")
        if span_entries:
            document.span_map.extend_from_offset_map(span_entries)
        else:
            for entry in normalized.span_map.to_list():
                document.span_map.add(
                    entry["raw_start"],
                    entry["raw_end"],
                    entry["canonical_start"],
                    entry["canonical_end"],
                    entry["transform"],
                    page=entry.get("page"),
                    bbox=entry.get("bbox"),
                )
        if provenance := metadata.get("provenance"):
            document.provenance.update(provenance)
        return document

    def _add_blocks(
        self,
        document: DocumentIR,
        blocks: Sequence[tuple[str, str, str | None, dict[str, Any]]],
        *,
        separator: str = "\n\n",
    ) -> None:
        offset = 0
        sep_len = len(separator)
        for index, (block_type, text, section, meta) in enumerate(blocks):
            normalized = self.normalizer.normalize(text)
            start = offset
            end = start + len(normalized.text)
            document.add_block(
                Block(
                    type=block_type,
                    text=normalized.text,
                    start=start,
                    end=end,
                    section=section,
                    meta=meta,
                )
            )
            offset = end
            if index < len(blocks) - 1:
                offset += sep_len


class ClinicalTrialsBuilder(IrBuilder):
    """Builds IR documents from ClinicalTrials.gov payloads."""

    def build_from_study(self, *, doc_id: str, uri: str, study: Mapping[str, Any]) -> DocumentIR:
        sections: list[tuple[str, str, str | None, dict[str, Any]]] = []
        for field, section in (
            ("title", "title"),
            ("status", "status"),
            ("eligibility", "eligibility"),
            ("outcomes", "outcomes"),
        ):
            value = study.get(field)
            if not value:
                continue
            text = value if isinstance(value, str) else "\n".join(str(v) for v in value)
            sections.append(("heading" if field == "title" else "paragraph", text, section, {"raw": value}))

        combined_text = "\n\n".join(section[1] for section in sections) if sections else ""
        document = super().build(
            doc_id=doc_id,
            source="clinicaltrials",
            uri=uri,
            text=combined_text,
            metadata={"provenance": study.get("provenance", {})},
        )
        self._add_blocks(document, sections)

        outcomes = study.get("outcomes") or []
        if isinstance(outcomes, Sequence) and outcomes:
            headers = ["measure", "description", "time_frame"]
            rows = [
                [
                    str(outcome.get("measure", "")),
                    str(outcome.get("description", "")),
                    str(outcome.get("timeFrame", "")),
                ]
                for outcome in outcomes or []
            ]
            caption = "Primary Outcomes"
            start = len(document.text)
            end = start + len(caption)
            document.add_table(Table(caption=caption, headers=headers, rows=rows, start=start, end=end, meta={}))
        return document


class PmcBuilder(IrBuilder):
    """Builds IR documents from PMC article payloads."""

    def build_from_article(self, *, doc_id: str, uri: str, article: Mapping[str, Any]) -> DocumentIR:
        abstract = article.get("abstract", "") or ""
        sections_payload = article.get("sections", [])
        parts = [abstract] if abstract else []
        parts.extend(section.get("text", "") for section in sections_payload)
        combined_text = "\n\n".join(part for part in parts if part)
        metadata = {
            "provenance": article.get("provenance", {}),
            "span_map": article.get("span_map", []),
        }
        document = super().build(doc_id=doc_id, source="pmc", uri=uri, text=combined_text, metadata=metadata)
        sections: list[tuple[str, str, str | None, dict[str, Any]]] = []
        if abstract:
            sections.append(("paragraph", abstract, "abstract", {"heading": "Abstract"}))
        for block in sections_payload:
            heading = block.get("heading", "")
            block_text = block.get("text", "")
            section = section_from_heading(heading) if heading else "body"
            sections.append(("heading" if heading else "paragraph", block_text, section, {"heading": heading}))
        self._add_blocks(document, sections, separator="\n\n")

        for table_payload in article.get("tables", []):
            caption = str(table_payload.get("caption", ""))
            headers = [str(header) for header in table_payload.get("headers", [])]
            rows = [[str(cell) for cell in row] for row in table_payload.get("rows", [])]
            start = len(document.text)
            end = start + len(caption)
            document.add_table(Table(caption=caption, headers=headers, rows=rows, start=start, end=end, meta={}))
        return document


class DailyMedBuilder(IrBuilder):
    """Builds IR documents from DailyMed SPL payloads."""

    def build_from_spl(self, *, doc_id: str, uri: str, spl: Mapping[str, Any]) -> DocumentIR:
        sections = spl.get("sections", [])
        combined_text = "\n\n".join(section.get("text", "") for section in sections)
        document = super().build(
            doc_id=doc_id,
            source="dailymed",
            uri=uri,
            text=combined_text,
            metadata={"provenance": spl.get("provenance", {})},
        )

        block_payloads: list[tuple[str, str, str | None, dict[str, Any]]] = []
        for section in sections:
            loinc = section.get("loinc")
            text = section.get("text", "")
            block_payloads.append(("paragraph", text, "loinc_section", {"loinc": loinc}))
        self._add_blocks(document, block_payloads)

        if ingredients := spl.get("ingredients"):
            headers = ["name", "strength", "basis"]
            rows = [[str(item.get(header, "")) for header in headers] for item in ingredients]
            caption = "Ingredients"
            start = len(document.text)
            end = start + len(caption)
            document.add_table(Table(caption=caption, headers=headers, rows=rows, start=start, end=end, meta={}))
        return document


class MinerUBuilder(IrBuilder):
    """Builds IR documents from MinerU artifact bundles."""

    def build_from_artifacts(self, *, doc_id: str, uri: str, artifacts: Mapping[str, Any]) -> DocumentIR:
        markdown = artifacts.get("markdown", "")
        document = super().build(
            doc_id=doc_id,
            source="mineru",
            uri=uri,
            text=markdown,
            metadata={
                "provenance": artifacts.get("provenance", {}),
                "span_map": artifacts.get("offset_map", []),
            },
        )

        canonical_text = document.text
        cursor = 0
        for block in artifacts.get("blocks", []):
            block_text = str(block.get("text", ""))
            normalized_block = self.normalizer.normalize(block_text).text
            if not normalized_block:
                continue
            start = canonical_text.find(normalized_block, cursor)
            if start == -1:
                start = cursor
            end = start + len(normalized_block)
            cursor = end
            document.add_block(
                Block(
                    type=str(block.get("type", "paragraph")),
                    text=normalized_block,
                    start=start,
                    end=end,
                    section=block.get("section"),
                    meta={"path": block.get("path")},
                )
            )

        for table_payload in artifacts.get("tables", []):
            caption = str(table_payload.get("caption", ""))
            headers = [str(header) for header in table_payload.get("headers", [])]
            rows = [[str(cell) for cell in row] for row in table_payload.get("rows", [])]
            start = len(document.text)
            end = start + len(caption)
            document.add_table(
                Table(
                    caption=caption,
                    headers=headers,
                    rows=rows,
                    start=start,
                    end=end,
                    meta={"page": table_payload.get("page")},
                )
            )
        return document


class _FallbackGuidelineParser(HTMLParser):
    """Minimal HTML parser that extracts semantic blocks and tables."""

    def __init__(self) -> None:
        super().__init__()
        self.blocks: List[Tuple[str, str, str | None, dict[str, Any]]] = []
        self.tables: List[dict[str, Any]] = []
        self._current_tag: str | None = None
        self._buffer: list[str] = []
        self._current_table: dict[str, Any] | None = None
        self._current_row: list[str] | None = None
        self._row_is_header = False
        self._capturing_caption = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"h1", "h2", "h3", "p", "li"}:
            self._flush_block()
            self._current_tag = tag
            self._buffer = []
        elif tag == "table":
            self._flush_block()
            self._current_table = {"headers": [], "rows": []}
        elif tag == "caption" and self._current_table is not None:
            self._buffer = []
            self._capturing_caption = True
        elif tag == "tr" and self._current_table is not None:
            self._current_row = []
            self._row_is_header = False
        elif tag in {"th", "td"} and self._current_table is not None and self._current_row is not None:
            self._buffer = []
            if tag == "th":
                self._row_is_header = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"h1", "h2", "h3", "p", "li"}:
            text = "".join(self._buffer).strip()
            if text:
                section = (
                    tag if tag in {"h1", "h2", "h3"} else ("list_item" if tag == "li" else "paragraph")
                )
                block_type = "heading" if tag in {"h1", "h2", "h3"} else section
                self.blocks.append((block_type, text, section, {"tag": tag}))
            self._current_tag = None
            self._buffer = []
        elif tag == "table" and self._current_table is not None:
            self.tables.append(self._current_table)
            self._current_table = None
        elif tag in {"th", "td"} and self._current_table is not None and self._current_row is not None:
            text = "".join(self._buffer).strip()
            self._current_row.append(text)
            self._buffer = []
        elif tag == "tr" and self._current_table is not None and self._current_row is not None:
            if self._row_is_header and not self._current_table["headers"]:
                self._current_table["headers"] = self._current_row
            else:
                self._current_table.setdefault("rows", []).append(self._current_row)
            self._current_row = None
        elif tag == "caption" and self._current_table is not None and self._capturing_caption:
            self._current_table["caption"] = "".join(self._buffer).strip()
            self._buffer = []
            self._capturing_caption = False

    def handle_data(self, data: str) -> None:
        if self._current_tag is not None or self._current_row is not None or self._capturing_caption:
            self._buffer.append(data)

    def close(self) -> None:  # pragma: no cover - HTMLParser base close is noop
        self._flush_block()
        super().close()

    def _flush_block(self) -> None:
        if self._current_tag is None:
            return
        text = "".join(self._buffer).strip()
        if text:
            section = (
                self._current_tag if self._current_tag in {"h1", "h2", "h3"} else (
                    "list_item" if self._current_tag == "li" else "paragraph"
                )
            )
            block_type = "heading" if self._current_tag in {"h1", "h2", "h3"} else section
            self.blocks.append((block_type, text, section, {"tag": self._current_tag}))
        self._current_tag = None
        self._buffer = []


class GuidelineBuilder(IrBuilder):
    """Builds IR documents from HTML guideline content."""

    def _parse_html(self, html: str) -> tuple[
        list[tuple[str, str, str | None, dict[str, Any]]],
        list[dict[str, Any]],
    ]:
        if BeautifulSoup is not None:
            soup = BeautifulSoup(html, "html.parser")
            blocks: list[tuple[str, str, str | None, dict[str, Any]]] = []
            for element in soup.find_all(["h1", "h2", "h3", "p", "li"]):
                text = element.get_text(strip=True)
                if not text:
                    continue
                if element.name in {"h1", "h2", "h3"}:
                    section = element.name
                    block_type = "heading"
                elif element.name == "li":
                    section = "list_item"
                    block_type = "list_item"
                else:
                    section = "paragraph"
                    block_type = "paragraph"
                blocks.append((block_type, text, section, {"tag": element.name}))
            tables: list[dict[str, Any]] = []
            for table_tag in soup.find_all("table"):
                headers: list[str] = []
                header_row = table_tag.find("tr")
                if header_row:
                    headers = [cell.get_text(strip=True) for cell in header_row.find_all(["th", "td"])]
                rows: list[list[str]] = []
                for row in table_tag.find_all("tr")[1:]:
                    rows.append([cell.get_text(strip=True) for cell in row.find_all(["th", "td"])])
                caption = table_tag.find("caption")
                tables.append(
                    {
                        "caption": caption.get_text(strip=True) if caption else "Guideline Table",
                        "headers": headers,
                        "rows": rows,
                    }
                )
            return blocks, tables

        parser = _FallbackGuidelineParser()
        parser.feed(html)
        parser.close()
        return parser.blocks, parser.tables

    def build_from_html(self, *, doc_id: str, uri: str, html: str) -> DocumentIR:
        blocks, tables = self._parse_html(html)
        combined_text = "\n\n".join(block[1] for block in blocks)
        document = super().build(
            doc_id=doc_id,
            source="guideline",
            uri=uri,
            text=combined_text,
            metadata={},
        )
        self._add_blocks(document, blocks)

        for table_payload in tables:
            caption = str(table_payload.get("caption", "Guideline Table"))
            headers = [str(value) for value in table_payload.get("headers", [])]
            rows = [[str(cell) for cell in row] for row in table_payload.get("rows", [])]
            start = len(document.text)
            end = start + len(caption)
            document.add_table(Table(caption=caption, headers=headers, rows=rows, start=start, end=end, meta={}))
        return document
