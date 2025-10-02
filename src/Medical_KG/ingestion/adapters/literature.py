from __future__ import annotations

import re
from collections.abc import AsyncIterator
from typing import Any

from bs4 import BeautifulSoup

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.adapters.http import HttpAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.utils import canonical_json, normalize_text

PUBMED_SEARCH_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
PUBMED_SUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
PMC_LIST_URL = "https://www.ncbi.nlm.nih.gov/pmc/oai/oai.cgi"
MEDRXIV_URL = "https://api.medrxiv.org/details/medrxiv"

PMID_RE = re.compile(r"^\d{4,}")
PMCID_RE = re.compile(r"^PMC\d+")


class PubMedAdapter(HttpAdapter):
    source = "pubmed"

    def __init__(self, context: AdapterContext, client: AsyncHttpClient, *, api_key: str | None = None) -> None:
        super().__init__(context, client)
        self.api_key = api_key

    async def fetch(self, term: str, retmax: int = 100) -> AsyncIterator[Any]:
        params = {"db": "pubmed", "retmode": "json", "retmax": retmax, "term": term}
        if self.api_key:
            params["api_key"] = self.api_key
        search = await self.fetch_json(PUBMED_SEARCH_URL, params=params)
        ids = search["esearchresult"].get("idlist", [])
        if not ids:
            return
        summary_params = {"db": "pubmed", "retmode": "json", "id": ",".join(ids)}
        if self.api_key:
            summary_params["api_key"] = self.api_key
        summary = await self.fetch_json(PUBMED_SUMMARY_URL, params=summary_params)
        result = summary.get("result", {})
        for uid in result.get("uids", []):
            data = result.get(uid)
            if data:
                yield data

    def parse(self, raw: Any) -> Document:
        uid = raw.get("uid") or raw["articleids"][0]["value"]
        title = normalize_text(raw.get("title", ""))
        abstract = normalize_text(raw.get("elocationid", ""))
        payload = {
            "pmid": uid,
            "title": title,
            "abstract": abstract,
            "pubdate": raw.get("pubdate"),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=uid, version=raw.get("sortpubdate", "unknown"), content=content)
        metadata = {
            "title": title,
            "pub_date": raw.get("pubdate"),
            "journal": raw.get("fulljournalname"),
        }
        return Document(doc_id=doc_id, source=self.source, content=abstract or title, metadata=metadata, raw=payload)

    def validate(self, document: Document) -> None:
        pmid = document.raw["pmid"]  # type: ignore[index]
        if not PMID_RE.match(str(pmid)):
            raise ValueError(f"Invalid PMID: {pmid}")


class PmcAdapter(HttpAdapter):
    source = "pmc"

    async def fetch(self, set_spec: str, *, metadata_prefix: str = "oai_dc") -> AsyncIterator[Any]:
        params = {"verb": "ListRecords", "set": set_spec, "metadataPrefix": metadata_prefix}
        xml = await self.fetch_text(PMC_LIST_URL, params=params)
        soup = BeautifulSoup(xml, "xml")
        for record in soup.find_all("record"):
            yield record

    def parse(self, raw: Any) -> Document:
        header = raw.find("header")
        identifier = header.find("identifier").text  # type: ignore[assignment]
        pmcid = identifier.split(":")[-1]
        metadata = raw.find("metadata")
        title = metadata.find("title").text if metadata else ""
        description = metadata.find("description").text if metadata else ""
        payload = {
            "pmcid": pmcid,
            "title": normalize_text(title),
            "description": normalize_text(description),
        }
        content = canonical_json(payload)
        doc_id = self.build_doc_id(identifier=pmcid, version=header.find("datestamp").text, content=content)  # type: ignore[arg-type]
        meta = {"title": payload["title"], "datestamp": header.find("datestamp").text}
        return Document(doc_id=doc_id, source=self.source, content=payload["description"] or payload["title"], metadata=meta, raw=payload)

    def validate(self, document: Document) -> None:
        pmcid = document.raw["pmcid"]  # type: ignore[index]
        if not PMCID_RE.match(pmcid):
            raise ValueError(f"Invalid PMCID: {pmcid}")


class MedRxivAdapter(HttpAdapter):
    source = "medrxiv"

    async def fetch(self, start: int = 0, chunk: int = 100) -> AsyncIterator[Any]:
        params = {"from": start, "chunk": chunk}
        payload = await self.fetch_json(MEDRXIV_URL, params=params)
        for record in payload.get("results", []):
            yield record

    def parse(self, raw: Any) -> Document:
        identifier = raw["doi"]
        title = normalize_text(raw.get("title", ""))
        abstract = normalize_text(raw.get("abstract", ""))
        payload = {
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
        if "/" not in document.raw["doi"]:  # type: ignore[index]
            raise ValueError("Invalid DOI")
