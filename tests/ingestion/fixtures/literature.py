from __future__ import annotations

from copy import deepcopy
from typing import Any

from . import load_json_fixture, load_text_fixture

_PUBMED_SEARCH = load_json_fixture("pubmed_search.json")
_PUBMED_SUMMARY = load_json_fixture("pubmed_summary.json")
_PUBMED_FETCH_XML = load_text_fixture("pubmed_fetch.xml")
_PMC_RECORD_XML = load_text_fixture("pmc_record.xml")
_MEDRXIV_RECORD = load_json_fixture("medrxiv.json")


def pubmed_search_payload() -> dict[str, Any]:
    return deepcopy(_PUBMED_SEARCH)


def pubmed_summary_payload() -> dict[str, Any]:
    return deepcopy(_PUBMED_SUMMARY)


def pubmed_fetch_xml() -> str:
    return _PUBMED_FETCH_XML


def pmc_record_xml() -> str:
    return _PMC_RECORD_XML


def medrxiv_record() -> dict[str, Any]:
    payload = deepcopy(_MEDRXIV_RECORD)
    results = payload.get("results", [])
    return deepcopy(results[0]) if results else {}


def medrxiv_record_without_date() -> dict[str, Any]:
    record = medrxiv_record()
    record.pop("date", None)
    return record


def pubmed_summary_without_history() -> dict[str, Any]:
    payload = pubmed_summary_payload()
    payload["result"]["uids"] = payload["result"].get("uids", [])[:2]
    return payload


def pubmed_search_without_history() -> dict[str, Any]:
    payload = pubmed_search_payload()
    result = payload.setdefault("esearchresult", {})
    result.pop("webenv", None)
    result.pop("querykey", None)
    result["count"] = "0"
    return payload


def pubmed_document_with_optional_fields() -> dict[str, Any]:
    return {
        "pmid": "12345678",
        "uid": "12345678",
        "title": "Lactate Guided Therapy",
        "abstract": "Clinical trial findings",
        "authors": ["Alice Example", "Bob Example"],
        "mesh_terms": ["Sepsis"],
        "pub_types": ["Journal Article"],
        "pmcid": "PMC1234567",
        "doi": "10.1000/example.doi",
        "journal": "Critical Care",
        "pub_year": "2024",
        "pubdate": "2024 Jan",
        "sortpubdate": "2024/01/01",
    }


def pubmed_document_without_optional_fields() -> dict[str, Any]:
    return {
        "pmid": "87654321",
        "uid": "87654321",
        "title": "Minimal Record",
        "abstract": "Abbreviated abstract",
        "authors": ["Case Minimal"],
        "mesh_terms": ["Intensive Care"],
        "pub_types": ["Journal Article"],
    }


__all__ = [
    "pubmed_search_payload",
    "pubmed_summary_payload",
    "pubmed_fetch_xml",
    "pmc_record_xml",
    "medrxiv_record",
    "medrxiv_record_without_date",
    "pubmed_summary_without_history",
    "pubmed_search_without_history",
    "pubmed_document_with_optional_fields",
    "pubmed_document_without_optional_fields",
]
