"""IR builders for ingestion sources with typed payload extraction support.

``IrBuilder`` now enforces the typed raw payload contract.  Callers must supply
the adapter payload union via the ``raw`` argument; omitting it raises a
``ValueError`` so legacy coercion paths cannot silently resurface::

    builder = IrBuilder()
    document = builder.build(
        doc_id="pubmed:123",
        source="pubmed",
        uri="https://pubmed.ncbi.nlm.nih.gov/123/",
        text="",
        raw=pubmed_payload,
    )
"""

from __future__ import annotations

import json
from collections.abc import Mapping, MutableMapping, Sequence
from html.parser import HTMLParser
from typing import Any, List, Tuple

from Medical_KG.utils.optional_dependencies import MissingDependencyError, optional_import

try:  # pragma: no cover - optional dependency
    optional_import(
        "bs4",
        feature_name="html-parsing",
        package_name="beautifulsoup4",
    )
except MissingDependencyError:  # pragma: no cover - fallback to stdlib parser
    BS4_AVAILABLE = False
else:
    from bs4 import BeautifulSoup  # noqa: F401

    BS4_AVAILABLE = True

from Medical_KG.ingestion.types import (
    AdapterDocumentPayload,
    ClinicalCatalogDocumentPayload,
    GuidelineDocumentPayload,
    JSONMapping,
    JSONValue,
    LiteratureDocumentPayload,
    is_clinical_document_payload,
    is_clinical_payload,
    is_guideline_payload,
    is_literature_payload,
    is_medrxiv_payload,
    is_nice_guideline_payload,
    is_pmc_payload,
    is_pubmed_payload,
    is_uspstf_payload,
)
from Medical_KG.ir.models import Block, DocumentIR, SpanMap, Table
from Medical_KG.ir.normalizer import TextNormalizer, section_from_heading


class IrBuilder:
    """Base builder converting source payloads into IR objects.

    ``build()`` accepts the optional ``raw`` payload union emitted by ingestion
    adapters. When provided the builder derives canonical text, semantic blocks,
    and provenance metadata directly from the typed payload while preserving the
    legacy behaviour for callers that omit ``raw``.
    """

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
        raw: AdapterDocumentPayload | None = None,
    ) -> DocumentIR:
        if raw is None:
            raise ValueError(
                "IrBuilder.build() requires a typed raw payload; ensure the adapter emitted DocumentRaw data."
            )
        if not isinstance(raw, Mapping):
            raise TypeError(
                "IrBuilder.build() received an unexpected raw payload type; expected a mapping produced by adapters."
            )
        (
            text_input,
            payload_blocks,
            payload_tables,
            payload_provenance,
        ) = self._prepare_payload(text, raw)
        return self._create_document_ir(
            doc_id=doc_id,
            source=source,
            uri=uri,
            text=text_input,
            metadata=metadata,
            blocks=payload_blocks,
            tables=payload_tables,
            payload_provenance=payload_provenance,
        )

    def _create_document_ir(
        self,
        *,
        doc_id: str,
        source: str,
        uri: str,
        text: str,
        metadata: Mapping[str, Any] | None,
        blocks: Sequence[tuple[str, str, str | None, dict[str, Any]]],
        tables: Sequence[tuple[str, list[str], list[list[str]], dict[str, Any]]],
        payload_provenance: Mapping[str, Any] | None,
    ) -> DocumentIR:
        metadata_mapping: Mapping[str, Any] = metadata if metadata is not None else {}
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
        span_entries = metadata_mapping.get("span_map")
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
        if provenance := metadata_mapping.get("provenance"):
            self._merge_provenance(document.provenance, provenance)
        if payload_provenance:
            self._merge_provenance(document.provenance, payload_provenance)
        if blocks:
            self._add_blocks(document, blocks)
        if tables:
            self._add_tables(document, tables)
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

    def _add_tables(
        self,
        document: DocumentIR,
        tables: Sequence[tuple[str, list[str], list[list[str]], dict[str, Any]]],
    ) -> None:
        for caption, headers, rows, meta in tables:
            start = len(document.text)
            end = start + len(caption)
            document.add_table(
                Table(caption=caption, headers=headers, rows=rows, start=start, end=end, meta=meta)
            )

    def _merge_provenance(
        self,
        target: MutableMapping[str, Any],
        update: Mapping[str, Any],
    ) -> None:
        for key, value in update.items():
            existing = target.get(key)
            if isinstance(existing, MutableMapping) and isinstance(value, Mapping):
                self._merge_provenance(existing, value)
                continue
            target[key] = value

    def _prepare_payload(
        self,
        text: str,
        raw: AdapterDocumentPayload,
    ) -> tuple[
        str,
        list[tuple[str, str, str | None, dict[str, Any]]],
        list[tuple[str, list[str], list[list[str]], dict[str, Any]]],
        dict[str, Any],
    ]:
        if is_literature_payload(raw):
            return self._prepare_literature_payload(text, raw)
        if is_clinical_payload(raw):
            return self._prepare_clinical_payload(text, raw)
        if is_guideline_payload(raw):
            return self._prepare_guideline_payload(text, raw)
        return text, [], [], {}

    def _prepare_literature_payload(
        self,
        default_text: str,
        raw: LiteratureDocumentPayload,
    ) -> tuple[
        str,
        list[tuple[str, str, str | None, dict[str, Any]]],
        list[tuple[str, list[str], list[list[str]], dict[str, Any]]],
        dict[str, Any],
    ]:
        blocks: list[tuple[str, str, str | None, dict[str, Any]]] = []
        provenance: dict[str, Any] = {}
        if is_pubmed_payload(raw):
            pubmed_parts: list[str] = []
            title = raw.get("title", "")
            if title:
                blocks.append(("heading", title, "title", {"pmid": raw["pmid"]}))
                pubmed_parts.append(title)
            abstract = raw.get("abstract", "")
            abstract_text = abstract or default_text
            if abstract_text:
                blocks.append(("paragraph", abstract_text, "abstract", {"pmid": raw["pmid"]}))
                pubmed_parts.append(abstract_text)
            provenance["pubmed"] = {"pmid": raw["pmid"]}
            if raw.get("pmcid"):
                provenance["pubmed"]["pmcid"] = raw["pmcid"]
            if raw.get("doi"):
                provenance["pubmed"]["doi"] = raw["doi"]
            if raw["mesh_terms"]:
                provenance["mesh_terms"] = list(raw["mesh_terms"])
            if raw["authors"]:
                provenance["authors"] = list(raw["authors"])
            combined_text = "\n\n".join(pubmed_parts) or default_text
            return combined_text, blocks, [], provenance
        if is_pmc_payload(raw):
            provenance["pmcid"] = raw["pmcid"]
            pmc_parts: list[str] = []
            title = raw.get("title", "")
            if title:
                blocks.append(("heading", title, "title", {"pmcid": raw["pmcid"]}))
                pmc_parts.append(title)
            abstract = raw.get("abstract", "")
            if abstract:
                blocks.append(("paragraph", abstract, "abstract", {"heading": "Abstract"}))
                pmc_parts.append(abstract)
            for section in raw.get("sections", []):
                heading = section.get("title", "").strip()
                text = section.get("text", "").strip()
                section_name = section_from_heading(heading) if heading else "body"
                if heading:
                    blocks.append(("heading", heading, section_name, {"heading": heading}))
                    pmc_parts.append(heading)
                if text:
                    meta: dict[str, Any] = {"heading": heading} if heading else {}
                    blocks.append(("paragraph", text, section_name, meta))
                    pmc_parts.append(text)
            combined_text = "\n\n".join(part for part in pmc_parts if part) or default_text
            return combined_text, blocks, [], provenance
        if is_medrxiv_payload(raw):
            provenance["medrxiv"] = {"doi": raw["doi"]}
            if raw.get("date"):
                provenance["medrxiv"]["date"] = raw["date"]
            medrxiv_parts: list[str] = []
            title = raw.get("title", "")
            if title:
                blocks.append(("heading", title, "title", {"doi": raw["doi"]}))
                medrxiv_parts.append(title)
            abstract = raw.get("abstract", "")
            combined_text = abstract or default_text
            if combined_text:
                blocks.append(("paragraph", combined_text, "abstract", {"doi": raw["doi"]}))
                medrxiv_parts.append(combined_text)
            final_text = "\n\n".join(medrxiv_parts) or combined_text or default_text
            return final_text, blocks, [], provenance
        return default_text, [], [], {}

    def _prepare_clinical_payload(
        self,
        default_text: str,
        raw: ClinicalCatalogDocumentPayload,
    ) -> tuple[
        str,
        list[tuple[str, str, str | None, dict[str, Any]]],
        list[tuple[str, list[str], list[list[str]], dict[str, Any]]],
        dict[str, Any],
    ]:
        if not is_clinical_document_payload(raw):
            return default_text, [], [], {}
        blocks: list[tuple[str, str, str | None, dict[str, Any]]] = []
        provenance: dict[str, Any] = {"nct_id": raw["nct_id"]}
        parts: list[str] = []
        title = raw.get("title", "")
        if title:
            blocks.append(("heading", title, "title", {"nct_id": raw["nct_id"]}))
            parts.append(title)
        status = raw.get("status")
        if status:
            status_text = f"Status: {status}"
            blocks.append(("paragraph", status_text, "status", {"status": status}))
            parts.append(status_text)
        phase = raw.get("phase")
        if phase:
            phase_text = f"Phase: {phase}"
            blocks.append(("paragraph", phase_text, "phase", {"phase": phase}))
            parts.append(phase_text)
        eligibility_text = self._stringify_json_value(raw.get("eligibility"))
        if eligibility_text:
            blocks.append(("paragraph", eligibility_text, "eligibility", {}))
            parts.append(eligibility_text)
        for index, arm in enumerate(raw.get("arms", [])):
            summary = self._summarize_mapping(arm)
            arm_meta: dict[str, Any] = {"arm_index": index}
            if arm_type := arm.get("armType"):
                arm_meta["arm_type"] = arm_type
            arm_meta["payload"] = arm
            blocks.append(("paragraph", summary, "arm", arm_meta))
            parts.append(summary)
        outcomes = raw.get("outcomes") or []
        for index, outcome in enumerate(outcomes):
            summary = self._summarize_mapping(outcome)
            outcome_meta: dict[str, Any] = {"outcome_index": index}
            if measure := outcome.get("measure"):
                outcome_meta["measure"] = measure
            if timeframe := outcome.get("timeFrame"):
                outcome_meta["time_frame"] = timeframe
            blocks.append(("paragraph", summary, "outcome", outcome_meta))
            parts.append(summary)
        combined_text = "\n\n".join(part for part in parts if part) or default_text
        return combined_text, blocks, [], provenance

    def _prepare_guideline_payload(
        self,
        default_text: str,
        raw: GuidelineDocumentPayload,
    ) -> tuple[
        str,
        list[tuple[str, str, str | None, dict[str, Any]]],
        list[tuple[str, list[str], list[list[str]], dict[str, Any]]],
        dict[str, Any],
    ]:
        blocks: list[tuple[str, str, str | None, dict[str, Any]]] = []
        provenance: dict[str, Any] = {}
        parts: list[str] = []
        if is_nice_guideline_payload(raw):
            provenance["guideline"] = {"uid": raw["uid"]}
            if raw.get("url"):
                provenance["guideline"]["url"] = raw["url"]
            if raw.get("licence"):
                provenance["guideline"]["licence"] = raw["licence"]
            title = raw.get("title", "")
            if title:
                blocks.append(("heading", title, "title", {"uid": raw["uid"]}))
                parts.append(title)
            summary = raw.get("summary", "")
            if summary:
                blocks.append(("paragraph", summary, "summary", {"uid": raw["uid"]}))
                parts.append(summary)
            combined_text = "\n\n".join(parts) or default_text
            return combined_text, blocks, [], provenance
        if is_uspstf_payload(raw):
            provenance["guideline"] = {}
            if raw.get("id"):
                provenance["guideline"]["id"] = raw["id"]
            if raw.get("url"):
                provenance["guideline"]["url"] = raw["url"]
            title = raw.get("title", "")
            if title:
                blocks.append(("heading", title, "title", {}))
                parts.append(title)
            status = raw.get("status")
            if status:
                status_text = f"Status: {status}"
                blocks.append(("paragraph", status_text, "status", {"status": status}))
                parts.append(status_text)
            combined_text = "\n\n".join(parts) or default_text
            return combined_text, blocks, [], provenance
        return default_text, [], [], {}

    @staticmethod
    def _summarize_mapping(value: JSONMapping) -> str:
        description = value.get("description")
        if isinstance(description, str) and description.strip():
            return description.strip()
        name = value.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
        label = value.get("label")
        if isinstance(label, str) and label.strip():
            return label.strip()
        return json.dumps(value, ensure_ascii=False, sort_keys=True)

    @staticmethod
    def _stringify_json_value(value: JSONValue | None) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        return json.dumps(value, ensure_ascii=False, sort_keys=True)


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
            sections.append(
                ("heading" if field == "title" else "paragraph", text, section, {"raw": value})
            )

        combined_text = "\n\n".join(section[1] for section in sections) if sections else ""
        document = self._create_document_ir(
            doc_id=doc_id,
            source="clinicaltrials",
            uri=uri,
            text=combined_text,
            metadata={"provenance": study.get("provenance", {})},
            blocks=sections,
            tables=(),
            payload_provenance=None,
        )

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
            document.add_table(
                Table(caption=caption, headers=headers, rows=rows, start=start, end=end, meta={})
            )
        return document


class PmcBuilder(IrBuilder):
    """Builds IR documents from PMC article payloads."""

    def build_from_article(
        self, *, doc_id: str, uri: str, article: Mapping[str, Any]
    ) -> DocumentIR:
        abstract = article.get("abstract", "") or ""
        sections_payload = article.get("sections", [])
        parts = [abstract] if abstract else []
        parts.extend(section.get("text", "") for section in sections_payload)
        combined_text = "\n\n".join(part for part in parts if part)
        metadata = {
            "provenance": article.get("provenance", {}),
            "span_map": article.get("span_map", []),
        }
        sections: list[tuple[str, str, str | None, dict[str, Any]]] = []
        if abstract:
            sections.append(("paragraph", abstract, "abstract", {"heading": "Abstract"}))
        for block in sections_payload:
            heading = block.get("heading", "")
            block_text = block.get("text", "")
            section = section_from_heading(heading) if heading else "body"
            sections.append(
                ("heading" if heading else "paragraph", block_text, section, {"heading": heading})
            )
        table_entries: list[tuple[str, list[str], list[list[str]], dict[str, Any]]] = []
        for table_payload in article.get("tables", []):
            caption = str(table_payload.get("caption", ""))
            headers = [str(header) for header in table_payload.get("headers", [])]
            rows = [[str(cell) for cell in row] for row in table_payload.get("rows", [])]
            table_entries.append((caption, headers, rows, {}))

        return self._create_document_ir(
            doc_id=doc_id,
            source="pmc",
            uri=uri,
            text=combined_text,
            metadata=metadata,
            blocks=sections,
            tables=table_entries,
            payload_provenance=None,
        )


class DailyMedBuilder(IrBuilder):
    """Builds IR documents from DailyMed SPL payloads."""

    def build_from_spl(self, *, doc_id: str, uri: str, spl: Mapping[str, Any]) -> DocumentIR:
        sections = spl.get("sections", [])
        combined_text = "\n\n".join(section.get("text", "") for section in sections)
        block_payloads: list[tuple[str, str, str | None, dict[str, Any]]] = []
        for section in sections:
            loinc = section.get("loinc")
            text = section.get("text", "")
            block_payloads.append(("paragraph", text, "loinc_section", {"loinc": loinc}))

        table_entries: list[tuple[str, list[str], list[list[str]], dict[str, Any]]] = []
        if ingredients := spl.get("ingredients"):
            headers = ["name", "strength", "basis"]
            rows = [[str(item.get(header, "")) for header in headers] for item in ingredients]
            table_entries.append(("Ingredients", headers, rows, {}))

        return self._create_document_ir(
            doc_id=doc_id,
            source="dailymed",
            uri=uri,
            text=combined_text,
            metadata={"provenance": spl.get("provenance", {})},
            blocks=block_payloads,
            tables=table_entries,
            payload_provenance=None,
        )


class MinerUBuilder(IrBuilder):
    """Builds IR documents from MinerU artifact bundles."""

    def build_from_artifacts(
        self, *, doc_id: str, uri: str, artifacts: Mapping[str, Any]
    ) -> DocumentIR:
        markdown = artifacts.get("markdown", "")
        document = self._create_document_ir(
            doc_id=doc_id,
            source="mineru",
            uri=uri,
            text=markdown,
            metadata={
                "provenance": artifacts.get("provenance", {}),
                "span_map": artifacts.get("offset_map", []),
            },
            blocks=(),
            tables=(),
            payload_provenance=None,
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
        elif (
            tag in {"th", "td"}
            and self._current_table is not None
            and self._current_row is not None
        ):
            self._buffer = []
            if tag == "th":
                self._row_is_header = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"h1", "h2", "h3", "p", "li"}:
            text = "".join(self._buffer).strip()
            if text:
                section = (
                    tag
                    if tag in {"h1", "h2", "h3"}
                    else ("list_item" if tag == "li" else "paragraph")
                )
                block_type = "heading" if tag in {"h1", "h2", "h3"} else section
                self.blocks.append((block_type, text, section, {"tag": tag}))
            self._current_tag = None
            self._buffer = []
        elif tag == "table" and self._current_table is not None:
            self.tables.append(self._current_table)
            self._current_table = None
        elif (
            tag in {"th", "td"}
            and self._current_table is not None
            and self._current_row is not None
        ):
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
        if (
            self._current_tag is not None
            or self._current_row is not None
            or self._capturing_caption
        ):
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
                self._current_tag
                if self._current_tag in {"h1", "h2", "h3"}
                else ("list_item" if self._current_tag == "li" else "paragraph")
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
        if BS4_AVAILABLE:
            from bs4 import BeautifulSoup as BS

            soup = BS(html, "html.parser")
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
                    headers = [
                        cell.get_text(strip=True) for cell in header_row.find_all(["th", "td"])
                    ]
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
        table_entries: list[tuple[str, list[str], list[list[str]], dict[str, Any]]] = []
        for table_payload in tables:
            caption = str(table_payload.get("caption", "Guideline Table"))
            headers = [str(value) for value in table_payload.get("headers", [])]
            rows = [[str(cell) for cell in row] for row in table_payload.get("rows", [])]
            table_entries.append((caption, headers, rows, {}))

        return self._create_document_ir(
            doc_id=doc_id,
            source="guideline",
            uri=uri,
            text=combined_text,
            metadata={},
            blocks=blocks,
            tables=table_entries,
            payload_provenance=None,
        )
