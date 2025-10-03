"""Shared typing utilities for ingestion adapters."""
from __future__ import annotations

from typing import Mapping, Sequence, TypedDict, Union

JSONPrimitive = Union[str, int, float, bool, None]
JSONValue = Union[JSONPrimitive, Mapping[str, "JSONValue"], Sequence["JSONValue"]]


class ClinicalDocumentPayload(TypedDict, total=False):
    nct_id: str
    title: str
    status: str | None
    phase: str
    study_type: str | None
    arms: Sequence[Mapping[str, JSONValue]]
    eligibility: JSONValue
    outcomes: Sequence[Mapping[str, JSONValue]]
    version: str


class OpenFdaDocumentPayload(TypedDict, total=False):
    identifier: str
    payload: Mapping[str, JSONValue]


class DailyMedDocumentPayload(TypedDict, total=False):
    setid: str
    title: str
    sections: Sequence[Mapping[str, JSONValue]]
    version: str


class RxNormDocumentPayload(TypedDict, total=False):
    identifier: str
    rxcui: str
    name: str
    synonyms: Sequence[str]
    properties: Mapping[str, JSONValue]


class PubMedDocumentPayload(TypedDict, total=False):
    pmid: str
    title: str
    abstract: str | None
    mesh_terms: Sequence[str]
    journal: str | None


class PmcDocumentPayload(TypedDict, total=False):
    pmcid: str
    title: str
    body: str
    sections: Sequence[Mapping[str, JSONValue]]


class MedRxivDocumentPayload(TypedDict, total=False):
    identifier: str
    title: str
    abstract: str | None
    posted: str | None


class GuidelineDocumentPayload(TypedDict, total=False):
    source_id: str
    title: str
    url: str | None
    body: str


class TerminologyDocumentPayload(TypedDict, total=False):
    concept_id: str
    label: str
    definition: str | None
    codes: Mapping[str, str]
    synonyms: Sequence[str]


AnyDocumentPayload = Union[
    ClinicalDocumentPayload,
    OpenFdaDocumentPayload,
    DailyMedDocumentPayload,
    RxNormDocumentPayload,
    PubMedDocumentPayload,
    PmcDocumentPayload,
    MedRxivDocumentPayload,
    GuidelineDocumentPayload,
    TerminologyDocumentPayload,
]
