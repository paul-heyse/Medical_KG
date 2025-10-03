from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from bs4 import BeautifulSoup

from Medical_KG.ir.models import Block, DocumentIR, Table
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
        document.span_map = normalized.span_map
        if span_entries := metadata.get("span_map"):
            document.span_map.extend_from_offset_map(span_entries)
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
                for outcome in outcomes  # type: ignore[arg-type]
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


class GuidelineBuilder(IrBuilder):
    """Builds IR documents from HTML guideline content."""

    def build_from_html(self, *, doc_id: str, uri: str, html: str) -> DocumentIR:
        soup = BeautifulSoup(html, "html.parser")
        content_blocks: list[tuple[str, str, str | None, dict[str, Any]]] = []
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
            content_blocks.append((block_type, text, section, {"tag": element.name}))

        combined_text = "\n\n".join(block[1] for block in content_blocks)
        document = super().build(
            doc_id=doc_id,
            source="guideline",
            uri=uri,
            text=combined_text,
            metadata={},
        )
        self._add_blocks(document, content_blocks)

        for table_tag in soup.find_all("table"):
            headers: list[str] = []
            header_row = table_tag.find("tr")
            if header_row:
                headers = [cell.get_text(strip=True) for cell in header_row.find_all(["th", "td"])]
            rows: list[list[str]] = []
            for row in table_tag.find_all("tr")[1:]:
                rows.append([cell.get_text(strip=True) for cell in row.find_all(["th", "td"])] or [])
            caption = table_tag.find("caption")
            caption_text = caption.get_text(strip=True) if caption else "Guideline Table"
            start = len(document.text)
            end = start + len(caption_text)
            document.add_table(Table(caption=caption_text, headers=headers, rows=rows, start=start, end=end, meta={}))
        return document
