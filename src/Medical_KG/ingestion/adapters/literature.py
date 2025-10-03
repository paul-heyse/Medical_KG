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
    MedRxivDocumentPayload,
    PmcDocumentPayload,
    PubMedDocumentPayload,
    is_medrxiv_payload,
    is_pmc_payload,
    is_pubmed_payload,
)
from Medical_KG.ingestion.utils import canonical_json, normalize_text

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PMC_LIST_URL = "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"
MEDRXIV_URL = "https://api.medrxiv.org/details/medrxiv"

PMID_RE = re.compile(r"^\d{4,}")
PMCID_RE = re.compile(r"^PMC\d+")


class PubMedAdapter(HttpAdapter[Any]):
    source = "pubmed"

    def __init__(self, context: AdapterContext, client: AsyncHttpClient, *, api_key: str | None = None) -> None:
        super().__init__(context, client)
        self.api_key = api_key
        host = urlparse(PUBMED_SEARCH_URL).netloc
        rate = RateLimit(rate=10 if api_key else 3, per=1.0)
        self.client.set_rate_limit(host, rate)

    async def fetch(self, term: str, retmax: int = 1000) -> AsyncIterator[Any]:
        retmax = min(retmax, 10000)
        params = {
            "db": "pubmed",
            "retmode": "json",
            "retmax": retmax,
            "term": term,
            "usehistory": "y",
        }
        if self.api_key:
            params["api_key"] = self.api_key
        search = await self.fetch_json(PUBMED_SEARCH_URL, params=params)
        search_result = search.get("esearchresult", {})
        webenv = search_result.get("webenv")
        query_key = search_result.get("querykey")
        count = int(search_result.get("count", len(search_result.get("idlist", [])) or 0))
        if not (webenv and query_key and count):
            id_list = search_result.get("idlist", [])
            if not id_list:
                return
            summary_params = {"db": "pubmed", "retmode": "json", "id": ",".join(id_list)}
            if self.api_key:
                summary_params["api_key"] = self.api_key
            summary = await self.fetch_json(PUBMED_SUMMARY_URL, params=summary_params)
            fetch_params = {"db": "pubmed", "retmode": "xml", "id": ",".join(id_list), "rettype": "abstract"}
            if self.api_key:
                fetch_params["api_key"] = self.api_key
            fetch_xml = await self.fetch_text(PUBMED_FETCH_URL, params=fetch_params)
            details = self._parse_fetch_xml(fetch_xml)
            summary_result = summary.get("result", {})
            for uid in summary_result.get("uids", []):
                combined = dict(details.get(uid, {}))
                combined.update(summary_result.get(uid, {}))
                if combined:
                    yield combined
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
            summary = await self.fetch_json(PUBMED_SUMMARY_URL, params=summary_params)
            summary_result = summary.get("result", {})
            uids: Iterable[str] = summary_result.get("uids", [])
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
                combined = dict(details.get(uid, {}))
                combined.update(summary_result.get(uid, {}))
                if combined:
                    yield combined
            retstart += retmax

    def parse(self, raw: Any) -> Document:
        uid = str(raw.get("pmid") or raw.get("uid"))
        title = normalize_text(raw.get("title", ""))
        abstract = normalize_text(raw.get("abstract", ""))
        payload: PubMedDocumentPayload = {
            "pmid": uid,
            "pmcid": raw.get("pmcid"),
            "doi": raw.get("doi"),
            "title": title,
            "abstract": abstract,
            "authors": raw.get("authors", []),
            "mesh_terms": raw.get("mesh_terms", []),
            "journal": raw.get("journal"),
            "pub_year": raw.get("pub_year"),
            "pub_types": raw.get("pub_types", []),
            "pubdate": raw.get("pubdate"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=uid, version=raw.get("sortpubdate", "unknown"), content=content)
        metadata = {
            "title": title,
            "pub_date": raw.get("pubdate"),
            "journal": raw.get("fulljournalname"),
            "pmid": uid,
        }
        return Document(doc_id=doc_id, source=self.source, content=abstract or title, metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        raw = document.raw
        if not is_pubmed_payload(raw):
            raise ValueError("PubMedAdapter document missing typed payload")
        pmid = raw["pmid"]
        if not PMID_RE.match(str(pmid)):
            raise ValueError(f"Invalid PMID: {pmid}")

    @staticmethod
    def _fetch_author_list(raw_authors: Iterable[dict[str, Any]]) -> list[str]:
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
    def _parse_fetch_xml(xml: str) -> dict[str, dict[str, Any]]:
        details: dict[str, dict[str, Any]] = {}
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
            journal = None
            pub_year = None
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
            details[pmid] = {
                "pmid": pmid,
                "title": normalize_text(article_data.findtext("ArticleTitle", default="")) if article_data is not None else "",
                "abstract": normalize_text("\n".join(filter(None, abstract_text))),
                "authors": authors,
                "mesh_terms": [term for term in mesh_terms if term],
                "journal": normalize_text(journal or ""),
                "pub_year": pub_year,
                "pub_types": [ptype for ptype in pub_types if ptype],
                "pmcid": pmcid,
                "doi": doi,
            }
        return details


class PmcAdapter(HttpAdapter[Any]):
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
    ) -> AsyncIterator[Any]:
        params: dict[str, Any] = {"verb": "ListRecords", "set": set_spec, "metadataPrefix": metadata_prefix}
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

    def parse(self, raw: Any) -> Document:
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
        meta = {"title": title, "datestamp": datestamp, "pmcid": pmcid}
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

    def _collect_sections(self, article: ET.Element | None) -> list[dict[str, str]]:
        sections: list[dict[str, str]] = []
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

    def _collect_table_like(self, article: ET.Element | None, name: str) -> list[dict[str, str]]:
        items: list[dict[str, str]] = []
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

    def _collect_references(self, article: ET.Element | None) -> list[dict[str, str]]:
        refs: list[dict[str, str]] = []
        if article is None:
            return refs
        for node in article.iter():
            if self._strip(node.tag) != "ref":
                continue
            label = normalize_text(self._findtext(node, "label") or "")
            citation = normalize_text(self._findtext(node, "mixed-citation") or "")
            refs.append({"label": label, "citation": citation})
        return refs


class MedRxivAdapter(HttpAdapter[Any]):
    source = "medrxiv"

    def __init__(
        self,
        context: AdapterContext,
        client: AsyncHttpClient,
        *,
        bootstrap_records: Iterable[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(context, client)
        self._bootstrap = list(bootstrap_records or [])

    async def fetch(
        self,
        *,
        search: str | None = None,
        cursor: str | None = None,
        page_size: int = 100,
    ) -> AsyncIterator[Any]:
        if self._bootstrap:
            for record in self._bootstrap:
                yield record
            return
        params: dict[str, Any] = {"page_size": page_size}
        if search:
            params["search"] = search
        next_cursor = cursor
        while True:
            if next_cursor:
                params["cursor"] = next_cursor
            payload = await self.fetch_json(MEDRXIV_URL, params=params)
            for record in payload.get("results", []):
                yield record
            next_cursor = payload.get("next_cursor")
            if not next_cursor:
                break

    def parse(self, raw: Any) -> Document:
        identifier = raw["doi"]
        title = normalize_text(raw.get("title", ""))
        abstract = normalize_text(raw.get("abstract", ""))
        payload: MedRxivDocumentPayload = {
            "doi": identifier,
            "title": title,
            "abstract": abstract,
            "date": raw.get("date"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=identifier, version=raw.get("version", "1"), content=content)
        metadata = {"title": title, "authors": raw.get("authors", [])}
        return Document(doc_id=doc_id, source=self.source, content=abstract or title, metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        raw = document.raw
        if not is_medrxiv_payload(raw):
            raise ValueError("MedRxiv document missing typed payload")
        doi = raw["doi"]
        if not isinstance(doi, str) or "/" not in doi:
            raise ValueError("Invalid DOI")


class LiteratureFallbackError(RuntimeError):
    """Raised when every literature adapter fails to return results."""


class LiteratureFallback:
    """Sequentially attempt literature adapters until one returns results."""

    def __init__(self, *adapters: HttpAdapter) -> None:
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
