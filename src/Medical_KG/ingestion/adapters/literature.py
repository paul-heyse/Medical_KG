"""Literature ingestion adapters with typed payload construction.

The adapters transform heterogeneous API responses into the TypedDict payloads
described in ``Medical_KG.ingestion.types``.  Raw responses remain ``Any`` at
fetch boundaries, but we immediately coerce them into JSON mappings or
sequences so that ``Document.raw`` adheres to the expected schema and mypy can
validate attribute access.  When payload fragments are already JSON-compatible
we use ``narrow_to_mapping`` or ``narrow_to_sequence`` instead of ``typing.cast``.
Inline comments call out the relevant ``Medical_KG.ingestion.types`` definitions
when optional fields require normalisation.

Optional field overview:

* PubMed frequently supplies ``doi``/``journal`` metadata; `pmcid` and
  `pubdate` are less consistent, so tests assert both populated and missing
  variants.
* MedRxiv exposes an optional ``date`` stamp that can be missing when records
  are embargoed.
* PMC records do not expose `NotRequired` keys but media elements may omit
  captions; the adapter normalises blank strings to keep downstream processing
  predictable.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import AsyncIterator, Mapping, Sequence as SequenceABC
from typing import Any, Iterable, Iterator
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

MappingABC = Mapping

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PUBMED_FETCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
PMC_LIST_URL = "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"
MEDRXIV_URL = "https://api.medrxiv.org/details/medrxiv"

PMID_RE = re.compile(r"^\d{4,}")
PMCID_RE = re.compile(r"^PMC\d+")


def _optional_str(value: object) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _string_list(values: object) -> list[str]:
    if not isinstance(values, list):
        return []
    return [normalize_text(str(item)) for item in values if isinstance(item, (str, int, float))]


class PubMedAdapter(HttpAdapter[Any]):
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
        # PubMed E-utilities (2024-01) emit JSON object envelopes for search and
        # summary endpoints; keep boundary validation so schema drift surfaces
        # during ingestion.
        search = ensure_json_mapping(
            await self.fetch_json(PUBMED_SEARCH_URL, params=params),
            context="pubmed search response",
        )
        search_result = ensure_json_mapping(
            search.get("esearchresult", {}),
            context="pubmed esearchresult",
        )
        id_list = [
            str(identifier)
            for identifier in ensure_json_sequence(
                search_result.get("idlist", []),
                context="pubmed search idlist",
            )
            if isinstance(identifier, (str, int))
        ]
        webenv = search_result.get("webenv")
        query_key = search_result.get("querykey")
        count_value = search_result.get("count")
        count = len(id_list)
        if isinstance(count_value, (str, int)):
            try:
                count = int(count_value)
            except ValueError:
                count = len(id_list)
        if not (
            isinstance(webenv, str)
            and isinstance(query_key, str)
            and count
        ):
            if not id_list:
                return
            summary_params: dict[str, object] = {"db": "pubmed", "retmode": "json", "id": ",".join(id_list)}
            if self.api_key:
                summary_params["api_key"] = self.api_key
            summary = ensure_json_mapping(
                await self.fetch_json(PUBMED_SUMMARY_URL, params=summary_params),
                context="pubmed summary response",
            )
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
            summary_result = ensure_json_mapping(
                summary.get("result", {}),
                context="pubmed summary result",
            )
            uids = [
                str(uid)
                for uid in ensure_json_sequence(
                    summary_result.get("uids", []),
                    context="pubmed summary uids",
                )
                if isinstance(uid, (str, int))
            ]
            for uid in uids:
                summary_entry = summary_result.get(uid)
                if summary_entry is None:
                    continue
                combined = dict(details.get(uid, {}))
                combined.update(ensure_json_mapping(summary_entry, context="pubmed summary entry"))
                if combined:
                    yield combined
            return
        retstart = 0
        while retstart < count:
            paged_summary_params: dict[str, object] = {
                "db": "pubmed",
                "retmode": "json",
                "retstart": retstart,
                "retmax": retmax,
                "query_key": query_key,
                "WebEnv": webenv,
            }
            if self.api_key:
                paged_summary_params["api_key"] = self.api_key
            summary = ensure_json_mapping(
                await self.fetch_json(PUBMED_SUMMARY_URL, params=paged_summary_params),
                context="pubmed summary response",
            )
            summary_result = ensure_json_mapping(
                summary.get("result", {}),
                context="pubmed summary result",
            )
            uids = [
                str(uid)
                for uid in ensure_json_sequence(
                    summary_result.get("uids", []),
                    context="pubmed summary uids",
                )
                if isinstance(uid, (str, int))
            ]
            paged_fetch_params: dict[str, object] = {
                "db": "pubmed",
                "retmode": "xml",
                "retstart": retstart,
                "retmax": retmax,
                "query_key": query_key,
                "WebEnv": webenv,
                "rettype": "abstract",
            }
            if self.api_key:
                paged_fetch_params["api_key"] = self.api_key
            fetch_xml = await self.fetch_text(PUBMED_FETCH_URL, params=paged_fetch_params)
            details = self._parse_fetch_xml(fetch_xml)
            for uid in uids:
                summary_entry = summary_result.get(uid)
                if summary_entry is None:
                    continue
                combined = dict(details.get(uid, {}))
                combined.update(ensure_json_mapping(summary_entry, context="pubmed summary entry"))
                if combined:
                    yield combined
            retstart += retmax

    def parse(self, raw: Any) -> Document:
        if not isinstance(raw, Mapping):
            raise TypeError("PubMed adapter expected a mapping payload")
        raw_map = dict(raw)
        uid_value = raw_map.get("pmid") or raw_map.get("uid")
        uid = str(uid_value) if uid_value is not None else "unknown"
        title = normalize_text(str(raw_map.get("title", "")))
        abstract = normalize_text(str(raw_map.get("abstract", "")))
        authors = _string_list(raw_map.get("authors", []))
        mesh_terms = _string_list(raw_map.get("mesh_terms", []))
        pub_types = _string_list(raw_map.get("pub_types", []))
        pmcid = _optional_str(raw_map.get("pmcid"))
        doi = _optional_str(raw_map.get("doi"))
        journal = _optional_str(raw_map.get("journal"))
        pub_year = _optional_str(raw_map.get("pub_year"))
        pubdate = _optional_str(raw_map.get("pubdate"))
        # ``PubMedDocumentPayload`` optional fields (``pmcid``, ``doi``,
        # ``journal``, ``pub_year`` and ``pubdate``) propagate ``None`` when the
        # upstream summary omits those keys.
        payload: PubMedDocumentPayload = {
            "pmid": uid,
            "pmcid": pmcid,
            "doi": doi,
            "title": title,
            "abstract": abstract,
            "authors": authors,
            "mesh_terms": mesh_terms,
            "journal": journal,
            "pub_year": pub_year,
            "pub_types": pub_types,
            "pubdate": pubdate,
        }
        content = canonical_json(payload)
        sort_version = str(raw_map.get("sortpubdate", "unknown"))
        doc_id = self.build_doc_id(identifier=uid, version=sort_version, content=content)
        metadata: MutableJSONMapping = {
            "title": title,
            "pub_date": pubdate,
            "journal": _optional_str(raw_map.get("fulljournalname")),
            "pmid": uid,
        }
        return Document(doc_id=doc_id, source=self.source, content=abstract or title, metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        raw = document.raw
        if is_pubmed_payload(raw):
            pubmed_payload = raw
        else:
            raise ValueError("PubMedAdapter document missing typed payload")
        pmid = pubmed_payload["pmid"]
        if not isinstance(pmid, (str, int)) or not PMID_RE.match(str(pmid)):
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

    def parse(self, raw: Any) -> Document:
        if not isinstance(raw, ET.Element):
            raise TypeError("PMC adapter expected an XML Element record")
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
        # ``PmcDocumentPayload`` fields mirror the schema documented in
        # ``Medical_KG.ingestion.types`` with sequences for every nested section.
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
        if is_pmc_payload(raw):
            pmc_payload = raw
        else:
            raise ValueError("PMC document missing typed payload")
        pmcid = pmc_payload["pmcid"]
        if not isinstance(pmcid, str) or not PMCID_RE.match(pmcid):
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
            response: JSONMapping = ensure_json_mapping(
                await self.fetch_json(MEDRXIV_URL, params=params),
                context="medrxiv response",
            )
            # medRxiv JSON API (2024-02 docs) returns paginated ``results`` arrays;
            # keep boundary validation to surface API changes quickly.
            for entry in ensure_json_sequence(response.get("results", []), context="medrxiv results"):
                if not isinstance(entry, MappingABC):
                    continue
                yield ensure_json_mapping(entry, context="medrxiv result entry")
            next_cursor_value = response.get("next_cursor")
            next_cursor = str(next_cursor_value) if isinstance(next_cursor_value, (str, int)) else None
            if not next_cursor:
                break

    def parse(self, raw: Any) -> Document:
        if not isinstance(raw, Mapping):
            raise TypeError("MedRxiv adapter expected a mapping payload")
        raw_map = dict(raw)
        identifier_value = raw_map.get("doi")
        if not isinstance(identifier_value, str):
            raise ValueError("MedRxiv payload missing DOI")
        identifier = identifier_value
        title = normalize_text(str(raw_map.get("title", "")))
        abstract = normalize_text(str(raw_map.get("abstract", "")))
        # ``MedRxivDocumentPayload.date`` is optional; ``_optional_str`` normalises
        # absent values to ``None`` per ``Medical_KG.ingestion.types``.
        payload: MedRxivDocumentPayload = {
            "doi": identifier,
            "title": title,
            "abstract": abstract,
            "date": _optional_str(raw_map.get("date")),
        }
        content = canonical_json(payload)
        version_value = raw_map.get("version", "1")
        doc_id = self.build_doc_id(identifier=identifier, version=str(version_value), content=content)
        authors = _string_list(raw_map.get("authors", []))
        metadata: MutableJSONMapping = {"title": title, "authors": authors}
        return Document(doc_id=doc_id, source=self.source, content=abstract or title, metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        raw = document.raw
        if is_medrxiv_payload(raw):
            medrxiv_payload = raw
        else:
            raise ValueError("MedRxiv document missing typed payload")
        doi = medrxiv_payload["doi"]
        if not isinstance(doi, str) or "/" not in doi:
            raise ValueError("Invalid DOI")

    @staticmethod
    def _iter_records(value: JSONValue | None) -> Iterator[JSONMapping]:
        if isinstance(value, SequenceABC) and not isinstance(value, (str, bytes, bytearray)):
            for item in value:
                if isinstance(item, Mapping):
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
