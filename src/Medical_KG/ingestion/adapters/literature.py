from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator
from typing import Any, Iterable
from urllib.parse import urlparse

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.adapters.http import HttpAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient, RateLimit
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.types import (
    JSONMapping,
    JSONValue,
    MedRxivDocumentPayload,
    MutableJSONMapping,
    PmcDocumentPayload,
    PmcMediaPayload,
    PmcReferencePayload,
    PmcSectionPayload,
    PubMedDocumentPayload,
    is_medrxiv_payload,
    is_pmc_payload,
    is_pubmed_payload,
)
from Medical_KG.ingestion.utils import (
    canonical_json,
    ensure_json_mapping,
    ensure_json_sequence,
    ensure_json_value,
    normalize_text,
)

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PMC_LIST_URL = "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"
MEDRXIV_URL = "https://api.medrxiv.org/details/medrxiv"

PMID_RE = re.compile(r"^\d{4,}")
PMCID_RE = re.compile(r"^PMC\d+")


class PubMedAdapter(HttpAdapter[JSONMapping]):
    source = "pubmed"

    def __init__(self, context: AdapterContext, client: AsyncHttpClient, *, api_key: str | None = None) -> None:
        super().__init__(context, client)
        self.api_key = api_key
        host = urlparse(PUBMED_SEARCH_URL).netloc
        rate = RateLimit(rate=10 if api_key else 3, per=1.0)
        self.client.set_rate_limit(host, rate)

    async def fetch(self, term: str, retmax: int = 1000) -> AsyncIterator[JSONMapping]:
        retmax = min(retmax, 10000)
        params: dict[str, object] = {
            "db": "pubmed",
            "retmode": "json",
            "retmax": retmax,
            "term": term,
            "usehistory": "y",
        }
        if self.api_key:
            params["api_key"] = self.api_key
        search_value = await self.fetch_json(PUBMED_SEARCH_URL, params=params)
        search = ensure_json_mapping(search_value, context="pubmed search response")
        search_result_value = search.get("esearchresult")
        if isinstance(search_result_value, MappingABC):
            search_result = ensure_json_mapping(search_result_value, context="pubmed search result")
        else:
            search_result = {}
        webenv = self._as_str(search_result.get("webenv"))
        query_key = self._as_str(search_result.get("querykey"))
        id_list = [
            uid
            for uid in (self._as_str(item) for item in self._iter_sequence(search_result.get("idlist")))
            if uid
        ]
        count = self._as_int(search_result.get("count")) or len(id_list)
        if not (webenv and query_key and count):
            if not id_list:
                return
            summary_params: dict[str, object] = {
                "db": "pubmed",
                "retmode": "json",
                "id": ",".join(id_list),
            }
            if self.api_key:
                summary_params["api_key"] = self.api_key
            summary_value = await self.fetch_json(PUBMED_SUMMARY_URL, params=summary_params)
            summary_uids, summary_records = self._extract_summary(summary_value)
            fetch_params: dict[str, object] = {
                "db": "pubmed",
                "retmode": "xml",
                "id": ",".join(id_list),
                "rettype": "abstract",
            }
            if self.api_key:
                fetch_params["api_key"] = self.api_key
            fetch_xml = await self.fetch_text(PUBMED_FETCH_URL, params=fetch_params)
            details = self._parse_fetch_xml(fetch_xml)
            for uid in (summary_uids or id_list):
                record = self._merge_records(uid, details, summary_records)
                if record:
                    yield record
            return
        retstart = 0
        while retstart < count:
            summary_params = {
                "db": "pubmed",
                "retmode": "json",
                "retstart": retstart,
                "retmax": retmax,
                "query_key": query_key,
                "WebEnv": webenv,
            }
            if self.api_key:
                summary_params["api_key"] = self.api_key
            summary_value = await self.fetch_json(PUBMED_SUMMARY_URL, params=summary_params)
            uids, summary_records = self._extract_summary(summary_value)
            if not uids:
                break
            fetch_params = {
                "db": "pubmed",
                "retmode": "xml",
                "retstart": retstart,
                "retmax": retmax,
                "query_key": query_key,
                "WebEnv": webenv,
                "rettype": "abstract",
            }
            if self.api_key:
                fetch_params["api_key"] = self.api_key
            fetch_xml = await self.fetch_text(PUBMED_FETCH_URL, params=fetch_params)
            details = self._parse_fetch_xml(fetch_xml)
            for uid in uids:
                record = self._merge_records(uid, details, summary_records)
                if record:
                    yield record
            retstart += retmax

    def parse(self, raw: JSONMapping) -> Document:
        uid = self._as_str(raw.get("pmid")) or self._as_str(raw.get("uid"))
        if not uid:
            raise ValueError("PubMed payload missing pmid")
        title = normalize_text(self._as_str(raw.get("title")) or "")
        abstract = normalize_text(self._as_str(raw.get("abstract")) or "")
        authors = [normalize_text(name) for name in self._iter_strings(raw.get("authors"))]
        mesh_terms = [normalize_text(term) for term in self._iter_strings(raw.get("mesh_terms"))]
        pub_types = [normalize_text(pub_type) for pub_type in self._iter_strings(raw.get("pub_types"))]
        payload: PubMedDocumentPayload = {
            "pmid": uid,
            "pmcid": self._as_str(raw.get("pmcid")),
            "doi": self._as_str(raw.get("doi")),
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "mesh_terms": mesh_terms,
            "journal": self._as_str(raw.get("journal")),
            "pub_year": self._as_str(raw.get("pub_year")),
            "pub_types": pub_types,
            "pubdate": self._as_str(raw.get("pubdate")),
        }
        content = canonical_json(payload)
        version = self._as_str(raw.get("sortpubdate")) or "unknown"
        metadata: MutableJSONMapping = {"title": title, "pmid": uid}
        if payload["pubdate"]:
            metadata["pub_date"] = payload["pubdate"]
        full_journal = self._as_str(raw.get("fulljournalname"))
        if full_journal:
            metadata["journal"] = full_journal
        doc_id = self.build_doc_id(identifier=uid, version=version, content=content)
        return Document(doc_id=doc_id, source=self.source, content=abstract or title, metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        raw = document.raw
        if not is_pubmed_payload(raw):
            raise ValueError("PubMedAdapter document missing typed payload")
        pmid = raw["pmid"]
        if not PMID_RE.match(str(pmid)):
            raise ValueError(f"Invalid PMID: {pmid}")

    @staticmethod
    def _as_str(value: JSONValue | None) -> str | None:
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        return None

    @staticmethod
    def _as_int(value: JSONValue | None) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            try:
                return int(value)
            except ValueError:
                return None
        return None

    @staticmethod
    def _fetch_author_list(raw_authors: Iterable[JSONMapping]) -> list[str]:
        authors: list[str] = []
        for author in raw_authors:
            if collective := author.get("CollectiveName"):
                authors.append(normalize_text(str(collective)))
                continue
            last = normalize_text(str(author.get("LastName", "")))
            fore = normalize_text(str(author.get("ForeName", "")))
            name = " ".join(part for part in [fore, last] if part)
            if name:
                authors.append(name)
        return authors

    @staticmethod
    def _parse_fetch_xml(xml: str) -> dict[str, JSONMapping]:
        details: dict[str, JSONMapping] = {}
        root = ET.fromstring(xml)

        def strip(tag: str) -> str:
            return tag.split("}")[-1]

        for article in root.findall(".//PubmedArticle"):
            medline = article.find("MedlineCitation")
            if medline is None:
                continue
            pmid = medline.findtext("PMID")
            if not pmid:
                continue
            article_data = medline.find("Article")
            journal: str | None = None
            pub_year: str | None = None
            abstract_text = []
            authors: list[str] = []
            pub_types: list[str] = []
            if article_data is not None:
                abstract = article_data.find("Abstract")
                if abstract is not None:
                    for chunk in abstract.findall("AbstractText"):
                        label = chunk.attrib.get("Label")
                        text = normalize_text("".join(chunk.itertext()))
                        abstract_text.append(f"{label}: {text}" if label else text)
                author_list = article_data.find("AuthorList")
                if author_list is not None:
                    authors = PubMedAdapter._fetch_author_list(
                        [
                            {
                                strip(child.tag): normalize_text("".join(child.itertext()))
                                for child in author
                            }
                            for author in author_list.findall("Author")
                        ]
                    )
                journal = article_data.findtext("Journal/Title")
                pub_year = article_data.findtext("Journal/JournalIssue/PubDate/Year")
                pub_types = [normalize_text(pt.text or "") for pt in article_data.findall("PublicationTypeList/PublicationType")]
            mesh_terms = [normalize_text(node.text or "") for node in medline.findall("MeshHeadingList/MeshHeading/DescriptorName")]
            article_ids = article.findall("PubmedData/ArticleIdList/ArticleId")
            pmcid = None
            doi = None
            for identifier in article_ids:
                id_type = identifier.attrib.get("IdType")
                value = normalize_text(identifier.text or "")
                if id_type == "pmc":
                    pmcid = value
                elif id_type == "doi":
                    doi = value
            detail: MutableJSONMapping = {
                "pmid": pmid,
                "title": normalize_text(article_data.findtext("ArticleTitle", default=""))
                if article_data is not None
                else "",
                "abstract": normalize_text("\n".join(filter(None, abstract_text))),
                "authors": authors,
                "mesh_terms": [term for term in mesh_terms if term],
                "journal": normalize_text(journal or ""),
                "pub_year": normalize_text(pub_year) if pub_year else None,
                "pub_types": [ptype for ptype in pub_types if ptype],
                "pmcid": pmcid,
                "doi": doi,
            }
            details[pmid] = detail
        return details


class PmcAdapter(HttpAdapter[ET.Element]):
    source = "pmc"

    def __init__(self, context: AdapterContext, client: AsyncHttpClient) -> None:
        super().__init__(context, client)
        host = urlparse(PMC_LIST_URL).netloc
        self.client.set_rate_limit(host, RateLimit(rate=3, per=1.0))

    async def fetch(
        self,
        set_spec: str,
        *,
        metadata_prefix: str = "pmc",
        from_date: str | None = None,
        until_date: str | None = None,
    ) -> AsyncIterator[ET.Element]:
        params: dict[str, object] = {"verb": "ListRecords", "set": set_spec, "metadataPrefix": metadata_prefix}
        if from_date:
            params["from"] = from_date
        if until_date:
            params["until"] = until_date
        while True:
            xml = await self.fetch_text(PMC_LIST_URL, params=params)
            root = ET.fromstring(xml)
            records = self._findall(root, "record")
            for record in records:
                yield record
            resumption = self._find(root, "resumptionToken")
            token = (resumption.text or "").strip() if resumption is not None else ""
            if not token:
                break
            params = {"verb": "ListRecords", "resumptionToken": token}

    def parse(self, raw: ET.Element) -> Document:
        header = self._find(raw, "header")
        identifier_text = self._findtext(header, "identifier") or ""
        pmcid = identifier_text.split(":")[-1] if identifier_text else "unknown"
        metadata = self._find(raw, "metadata")
        article = None
        if metadata is not None:
            article = self._find(metadata, "article") or metadata
        title = normalize_text(self._findtext(article, "article-title") or self._findtext(metadata, "title") or "")
        abstract = normalize_text(self._collect_text(article, "abstract")) if article is not None else ""
        sections = self._collect_sections(article)
        tables = self._collect_table_like(article, "table-wrap")
        figures = self._collect_table_like(article, "fig")
        references = self._collect_references(article)
        payload: PmcDocumentPayload = {
            "pmcid": pmcid,
            "title": title,
            "abstract": abstract,
            "sections": sections,
            "tables": tables,
            "figures": figures,
            "references": references,
        }
        content = canonical_json(payload)
        datestamp = self._findtext(header, "datestamp") or "unknown"
        doc_id = self.build_doc_id(identifier=pmcid, version=datestamp, content=content)
        meta: MutableJSONMapping = {"title": title, "datestamp": datestamp, "pmcid": pmcid}
        body_text = "\n\n".join(section["text"] for section in sections if section["text"])
        document_content = abstract or body_text or title
        return Document(doc_id=doc_id, source=self.source, content=document_content, metadata=meta, raw=payload)

    def validate(self, document: Document) -> None:
        raw = document.raw
        if not is_pmc_payload(raw):
            raise ValueError("PMC document missing typed payload")
        pmcid = raw["pmcid"]
        if not PMCID_RE.match(str(pmcid)):
            raise ValueError(f"Invalid PMCID: {pmcid}")

    @staticmethod
    def _strip(tag: str) -> str:
        return tag.split("}")[-1]

    def _find(self, element: ET.Element | None, name: str) -> ET.Element | None:
        if element is None:
            return None
        for child in element.iter():
            if self._strip(child.tag) == name:
                return child
        return None

    def _findall(self, element: ET.Element, name: str) -> list[ET.Element]:
        return [child for child in element.iter() if self._strip(child.tag) == name]

    def _findtext(self, element: ET.Element | None, name: str) -> str | None:
        if element is None:
            return None
        for child in element.iter():
            if self._strip(child.tag) == name:
                return "".join(child.itertext())
        return None

    def _collect_text(self, element: ET.Element | None, name: str) -> str:
        if element is None:
            return ""
        texts: list[str] = []
        for child in element.iter():
            if self._strip(child.tag) == name:
                texts.append(normalize_text("".join(child.itertext())))
        return "\n".join(texts)

    def _collect_sections(self, article: ET.Element | None) -> list[PmcSectionPayload]:
        sections: list[PmcSectionPayload] = []
        if article is None:
            return sections
        for section in article.iter():
            if self._strip(section.tag) != "sec":
                continue
            title = normalize_text(self._findtext(section, "title") or "")
            text_chunks = [normalize_text("".join(node.itertext())) for node in section if self._strip(node.tag) != "title"]
            text = "\n".join(chunk for chunk in text_chunks if chunk)
            sections.append({"title": title, "text": text})
        return sections

    def _collect_table_like(self, article: ET.Element | None, name: str) -> list[PmcMediaPayload]:
        items: list[PmcMediaPayload] = []
        if article is None:
            return items
        for node in article.iter():
            if self._strip(node.tag) != name:
                continue
            caption = normalize_text(self._findtext(node, "caption") or "")
            label = normalize_text(self._findtext(node, "label") or "")
            uri = None
            graphic = self._find(node, "graphic")
            if graphic is not None:
                uri = graphic.attrib.get("{http://www.w3.org/1999/xlink}href") or graphic.attrib.get("href")
            items.append({"label": label, "caption": caption, "uri": uri or ""})
        return items

    def _collect_references(self, article: ET.Element | None) -> list[PmcReferencePayload]:
        refs: list[PmcReferencePayload] = []
        if article is None:
            return refs
        for node in article.iter():
            if self._strip(node.tag) != "ref":
                continue
            label = normalize_text(self._findtext(node, "label") or "")
            citation = normalize_text(self._findtext(node, "mixed-citation") or "")
            refs.append({"label": label, "citation": citation})
        return refs


class MedRxivAdapter(HttpAdapter[JSONMapping]):
    source = "medrxiv"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[JSONMapping] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(
        self,
        *,
        search: str | None = None,
        cursor: str | None = None,
        page_size: int = 100,
    ) -> AsyncIterator[JSONMapping]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        params: dict[str, object] = {"page_size": page_size}
        if search:
            params["search"] = search
        next_cursor = cursor
        while True:
            if next_cursor:
                params["cursor"] = next_cursor
            payload_value = await self.fetch_json(MEDRXIV_URL, params=params)
            payload = ensure_json_mapping(payload_value, context="medrxiv response")
            results_value = payload.get("results")
            for record in self._iter_records(results_value):
                yield record
            next_cursor_value = payload.get("next_cursor")
            next_cursor = next_cursor_value if isinstance(next_cursor_value, str) else None
            if not next_cursor:
                break

    def parse(self, raw: JSONMapping) -> Document:
        identifier = self._as_str(raw.get("doi"))
        if not identifier:
            raise ValueError("MedRxiv payload missing doi")
        title = normalize_text(self._as_str(raw.get("title")) or "")
        abstract = normalize_text(self._as_str(raw.get("abstract")) or "")
        payload: MedRxivDocumentPayload = {
            "doi": identifier,
            "title": title,
            "abstract": abstract,
            "date": self._as_str(raw.get("date")),
        }
        content = canonical_json(payload)
        version = self._as_str(raw.get("version")) or "1"
        doc_id = self.build_doc_id(identifier=identifier, version=version, content=content)
        authors = [normalize_text(author) for author in self._iter_strings(raw.get("authors"))]
        metadata: MutableJSONMapping = {"title": title}
        if authors:
            metadata["authors"] = authors
        return Document(doc_id=doc_id, source=self.source, content=abstract or title, metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        raw = document.raw
        if not is_medrxiv_payload(raw):
            raise ValueError("MedRxiv document missing typed payload")
        doi = raw["doi"]
        if not isinstance(doi, str) or "/" not in doi:
            raise ValueError("Invalid DOI")

    @staticmethod
    def _iter_records(value: JSONValue | None) -> Iterator[JSONMapping]:
        if isinstance(value, SequenceABC) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                if isinstance(item, MappingABC):
                    yield ensure_json_mapping(
                        ensure_json_value(item, context="medrxiv record"),
                        context="medrxiv record mapping",
                    )

    @staticmethod
    def _iter_strings(value: JSONValue | None) -> Iterator[str]:
        if isinstance(value, SequenceABC) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                if isinstance(item, str):
                    yield item
                elif isinstance(item, (int, float)) and not isinstance(item, bool):
                    yield str(item)

    @staticmethod
    def _as_str(value: JSONValue | None) -> str | None:
        if isinstance(value, str):
            return value
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return str(value)
        return None


class LiteratureFallbackError(RuntimeError):
    """Raised when every literature adapter fails to return results."""


class LiteratureFallback:
    """Sequentially attempt literature adapters until one returns results."""

    def __init__(self, *adapters: HttpAdapter[Any]) -> None:
        if not adapters:
            raise ValueError("At least one adapter must be provided for fallback")
        self._adapters = list(adapters)

    async def run(self, **kwargs: Any) -> tuple[list[Document], str | None]:
        last_error: Exception | None = None
        for adapter in self._adapters:
            try:
                results = await adapter.run(**kwargs)
            except Exception as exc:  # pragma: no cover - exercised in tests
                last_error = exc
                continue
            docs = [result.document for result in results]
            if docs:
                return docs, adapter.source
        if last_error is not None:
            raise LiteratureFallbackError("All literature adapters failed") from last_error
        return [], None
