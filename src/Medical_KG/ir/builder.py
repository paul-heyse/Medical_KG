from __future__ import annotations

from typing import Any, Iterable, Mapping

from Medical_KG.ir.models import Block, DocumentIR, Table
from Medical_KG.ir.normalizer import TextNormalizer, section_from_heading


class IrBuilder:
    """Base builder converting source payloads into IR objects."""

    def __init__(self, *, normalizer: TextNormalizer | None = None) -> None:
        self.normalizer = normalizer or TextNormalizer()

    def build(self, *, doc_id: str, source: str, uri: str, text: str, metadata: Mapping[str, Any]) -> DocumentIR:
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
        document.provenance.update(metadata.get("provenance", {}))
        return document


class ClinicalTrialsBuilder(IrBuilder):
    def build_from_study(self, *, doc_id: str, uri: str, study: Mapping[str, Any]) -> DocumentIR:
        sections: list[tuple[str, str, str]] = []
        for name in ("title", "status", "eligibility"):
            value = study.get(name, "") or ""
            if value:
                normalized = self.normalizer.normalize(str(value))
                sections.append((name, normalized.text, str(value)))
        combined_text = "\n\n".join(section_text for _, section_text, _ in sections) if sections else ""
        document = super().build(doc_id=doc_id, source="clinicaltrials", uri=uri, text=combined_text, metadata={})
        offset = 0
        for index, (section, section_text, raw_value) in enumerate(sections):
            start = offset
            end = start + len(section_text)
            block_type = "heading" if section == "title" else "paragraph"
            document.add_block(
                Block(
                    type=block_type,
                    text=section_text,
                    start=start,
                    end=end,
                    section=section,
                    meta={"raw": raw_value},
                )
            )
            offset = end
            if index < len(sections) - 1:
                offset += 2  # account for double newline separator
        return document


class PmcBuilder(IrBuilder):
    def build_from_article(self, *, doc_id: str, uri: str, article: Mapping[str, Any]) -> DocumentIR:
        text = article.get("abstract", "")
        document = super().build(doc_id=doc_id, source="pmc", uri=uri, text=text, metadata={})
        blocks: Iterable[Mapping[str, Any]] = article.get("sections", [])  # type: ignore[assignment]
        offset = 0
        for block in blocks:
            heading = block.get("heading", "")
            normalized = self.normalizer.normalize(block.get("text", ""))
            start = offset
            end = start + len(normalized.text)
            document.add_block(
                Block(
                    type="heading" if heading else "paragraph",
                    text=normalized.text,
                    start=start,
                    end=end,
                    section=section_from_heading(heading) if heading else "body",
                    meta={"heading": heading},
                )
            )
            offset = end + 1
        for table_payload in article.get("tables", []):
            caption = table_payload.get("caption", "")
            headers = table_payload.get("headers", [])
            rows = table_payload.get("rows", [])
            start = offset
            end = start + len(caption)
            document.add_table(Table(caption=caption, headers=headers, rows=rows, start=start, end=end, meta={}))
            offset = end + 1
        return document
