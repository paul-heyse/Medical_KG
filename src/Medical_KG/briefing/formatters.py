"""Formatting helpers for dossier exports."""

from __future__ import annotations

import io
import json
from textwrap import indent
from typing import Mapping, Sequence
from xml.sax.saxutils import escape
from zipfile import ZipFile

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

DEFAULT_TOPIC_TITLE = "Untitled Briefing"
DEFAULT_SECTION_TITLE = "Untitled Section"
DEFAULT_CITATION_ID = "Unknown"


class BriefingFormatter:
    """Render dossier payloads into multiple formats.

    Missing or malformed fields degrade gracefully:

    - ``topic`` falls back to ``"Untitled Briefing"``
    - Section titles fall back to ``"Untitled Section"``
    - Citation identifiers fall back to ``"Unknown"``
    - Citation counts default to ``0``
    - Item summaries and descriptions default to an empty string
    """

    def __init__(self, *, stylesheet: str | None = None) -> None:
        self._stylesheet = stylesheet or "body { font-family: Arial, sans-serif; margin: 1.5rem; }"

    def to_json(self, payload: Mapping[str, object]) -> str:
        return json.dumps(payload, indent=2, sort_keys=True)

    def to_markdown(self, payload: Mapping[str, object]) -> str:
        """Return a Markdown dossier, defaulting missing values to readable placeholders."""

        topic = str(payload.get("topic", DEFAULT_TOPIC_TITLE))
        lines: list[str] = [f"# Topic Dossier: {topic}"]
        sections = payload.get("sections")
        if not isinstance(sections, Sequence) or isinstance(sections, (str, bytes)):
            sections = []
        for section in sections:
            if not isinstance(section, Mapping):
                continue
            title = str(section.get("title", DEFAULT_SECTION_TITLE))
            lines.append(f"\n## {title}")
            items = section.get("items")
            if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
                continue
            for entry in items:
                if not isinstance(entry, Mapping):
                    continue
                summary_value = entry.get("summary") or entry.get("description") or ""
                summary = str(summary_value).strip()
                if summary:
                    lines.append(f"- {summary}")
                citations = entry.get("citations")
                if not isinstance(citations, Sequence) or isinstance(citations, (str, bytes)):
                    continue
                citation_ids = []
                for citation in citations:
                    if not isinstance(citation, Mapping):
                        continue
                    citation_ids.append(str(citation.get("doc_id", DEFAULT_CITATION_ID)))
                if citation_ids:
                    lines.append(indent(f"Citations: {', '.join(citation_ids)}", "  "))
        lines.append("\n## Bibliography")
        bibliography = payload.get("bibliography")
        if isinstance(bibliography, Sequence) and not isinstance(bibliography, (str, bytes)):
            for citation in bibliography:
                if not isinstance(citation, Mapping):
                    continue
                doc_id = str(citation.get("doc_id", DEFAULT_CITATION_ID))
                count_value = citation.get("citation_count", 0)
                try:
                    count = int(count_value)
                except (TypeError, ValueError):
                    count = 0
                lines.append(f"- {doc_id} ({count} references)")
        return "\n".join(lines)

    def to_html(self, payload: Mapping[str, object]) -> str:
        """Return HTML output, filling in defaults for missing fields."""

        topic = escape(str(payload.get("topic", DEFAULT_TOPIC_TITLE)))
        body = [f"<h1>Topic Dossier: {topic}</h1>"]
        bibliography = payload.get("bibliography")
        sections = payload.get("sections")
        if not isinstance(sections, Sequence) or isinstance(sections, (str, bytes)):
            sections = []
        for section in sections:
            if not isinstance(section, Mapping):
                continue
            title = escape(str(section.get("title", DEFAULT_SECTION_TITLE)))
            body.append(f"<section><h2>{title}</h2><ul>")
            items = section.get("items")
            if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
                continue
            for entry in items:
                if not isinstance(entry, Mapping):
                    continue
                summary_value = entry.get("summary") or entry.get("description") or ""
                summary = escape(str(summary_value))
                citations = entry.get("citations")
                citation_html_parts: list[str] = []
                if isinstance(citations, Sequence) and not isinstance(citations, (str, bytes)):
                    for citation in citations:
                        if not isinstance(citation, Mapping):
                            continue
                        doc_id = escape(str(citation.get("doc_id", DEFAULT_CITATION_ID)))
                        quote = escape(str(citation.get("quote", "")))
                        citation_html_parts.append(
                            f"<li>[{doc_id}] <span class='quote'>{quote}</span></li>"
                        )
                citation_html = "".join(citation_html_parts)
                body.append(f"<li>{summary}<ul class='citations'>{citation_html}</ul></li>")
            body.append("</ul></section>")

        if isinstance(bibliography, Sequence) and not isinstance(bibliography, (str, bytes)):
            bib_items: list[str] = []
            for citation in bibliography:
                if not isinstance(citation, Mapping):
                    continue
                doc_id = escape(str(citation.get("doc_id", DEFAULT_CITATION_ID)))
                count_value = citation.get("citation_count", 0)
                try:
                    count = int(count_value)
                except (TypeError, ValueError):
                    count = 0
                bib_items.append(f"<li>{doc_id} ({count} refs)</li>")
            bib_html = "".join(bib_items)
            body.append(f"<section><h2>Bibliography</h2><ul>{bib_html}</ul></section>")
        return f"<html><head><style>{self._stylesheet}</style></head><body>{''.join(body)}</body></html>"

    def to_pdf(self, payload: Mapping[str, object]) -> bytes:
        """Return a PDF byte stream, skipping or defaulting missing metadata."""

        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        y = height - 72
        pdf.setFont("Helvetica-Bold", 16)
        topic = str(payload.get("topic", DEFAULT_TOPIC_TITLE))
        pdf.drawString(72, y, f"Topic Dossier: {topic}")
        y -= 36
        pdf.setFont("Helvetica", 11)
        sections = payload.get("sections")
        if not isinstance(sections, Sequence) or isinstance(sections, (str, bytes)):
            sections = []
        for section in sections:
            if not isinstance(section, Mapping):
                continue
            if y < 100:
                pdf.showPage()
                y = height - 72
                pdf.setFont("Helvetica", 11)
            pdf.setFont("Helvetica-Bold", 13)
            title = str(section.get("title", DEFAULT_SECTION_TITLE))
            pdf.drawString(72, y, title)
            y -= 24
            pdf.setFont("Helvetica", 11)
            items = section.get("items")
            if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
                continue
            for entry in items:
                if not isinstance(entry, Mapping):
                    continue
                summary_value = entry.get("summary") or entry.get("description") or ""
                summary = str(summary_value)
                if not summary:
                    continue
                pdf.drawString(90, y, summary)
                y -= 18
                if y < 100:
                    pdf.showPage()
                    y = height - 72
                    pdf.setFont("Helvetica", 11)
        pdf.showPage()
        pdf.save()
        return buffer.getvalue()

    def to_docx(self, payload: Mapping[str, object]) -> bytes:
        """Return a DOCX archive derived from the Markdown representation."""

        markdown = self.to_markdown(payload)
        return _markdown_to_docx(markdown)


def _markdown_to_docx(markdown: str) -> bytes:
    buffer = io.BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", _CONTENT_TYPES)
        archive.writestr("_rels/.rels", _RELS)
        archive.writestr("word/_rels/document.xml.rels", _DOC_RELS)
        archive.writestr("docProps/core.xml", _CORE)
        archive.writestr("word/document.xml", _markdown_to_document_xml(markdown))
        archive.writestr("word/styles.xml", _STYLES)
    return buffer.getvalue()


def _markdown_to_document_xml(markdown: str) -> str:
    paragraphs: list[str] = []
    for line in markdown.splitlines():
        text = escape(line or " ")
        paragraphs.append("<w:p><w:r><w:t xml:space='preserve'>{}</w:t></w:r></w:p>".format(text))
    content = "".join(paragraphs)
    return _DOCUMENT_TEMPLATE.format(content=content)


_CONTENT_TYPES = """<?xml version='1.0' encoding='UTF-8'?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
</Types>"""

_RELS = """<?xml version='1.0' encoding='UTF-8'?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
</Relationships>"""

_DOC_RELS = """<?xml version='1.0' encoding='UTF-8'?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

_CORE = """<?xml version='1.0' encoding='UTF-8'?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
                  xmlns:dc="http://purl.org/dc/elements/1.1/"
                  xmlns:dcterms="http://purl.org/dc/terms/"
                  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
                  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>Topic Dossier</dc:title>
  <cp:revision>1</cp:revision>
</cp:coreProperties>"""

_STYLES = """<?xml version='1.0' encoding='UTF-8'?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:default="1" w:styleId="Normal">
    <w:name w:val="Normal"/>
  </w:style>
</w:styles>"""

_DOCUMENT_TEMPLATE = """<?xml version='1.0' encoding='UTF-8'?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>{content}</w:body>
</w:document>"""


__all__ = ["BriefingFormatter"]
