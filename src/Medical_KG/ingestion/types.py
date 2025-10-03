"""Shared typing utilities for ingestion adapters."""
from __future__ import annotations

from typing import Mapping, MutableMapping, Sequence, TypedDict, Union


JSONPrimitive = Union[str, int, float, bool, None]
JSONValue = Union[JSONPrimitive, Mapping[str, "JSONValue"], Sequence["JSONValue"]]
JSONMapping = Mapping[str, JSONValue]
JSONSequence = Sequence[JSONValue]
MutableJSONMapping = MutableMapping[str, JSONValue]


class ClinicalTrialsStudyPayload(TypedDict, total=False):
    protocolSection: JSONMapping
    derivedSection: JSONMapping


class ClinicalDocumentPayload(TypedDict, total=False):
    nct_id: str
    title: str
    status: str | None
    phase: str | None
    study_type: str | None
    arms: Sequence[JSONMapping]
    eligibility: JSONValue
    outcomes: Sequence[JSONMapping]
    version: str
    lead_sponsor: str | None
    enrollment: int | str | None
    start_date: str | None
    completion_date: str | None


class OpenFdaRecordPayload(TypedDict, total=False):
    safetyreportid: str | None
    udi_di: str | None
    setid: str | None
    id: str | None
    receivedate: str | None
    version_number: str | None
    last_updated: str | None


class OpenFdaDocumentPayload(TypedDict, total=False):
    identifier: str
    version: str
    record: JSONMapping


class DailyMedSectionPayload(TypedDict, total=False):
    loinc: str | None
    text: str


class DailyMedDocumentPayload(TypedDict, total=False):
    setid: str
    title: str
    version: str
    sections: Sequence[DailyMedSectionPayload]


class RxNormDocumentPayload(TypedDict, total=False):
    rxcui: str
    name: str | None
    synonym: str | None
    tty: str | None
    ndc: str | None


class AccessGudidDocumentPayload(TypedDict, total=False):
    udi_di: str
    brand: str | None
    model: str | None
    company: str | None
    description: str | None


class NiceGuidelineDocumentPayload(TypedDict, total=False):
    uid: str
    title: str
    summary: str
    url: str | None
    licence: str | None


class UspstfDocumentPayload(TypedDict, total=False):
    id: str | None
    title: str
    status: str | None
    url: str | None


class CdcSocrataDocumentPayload(TypedDict, total=False):
    identifier: str
    record: JSONMapping


class CdcWonderDocumentPayload(TypedDict, total=False):
    rows: Sequence[Mapping[str, str]]


class WhoGhoDocumentPayload(TypedDict, total=False):
    indicator: str | None
    value: JSONValue
    country: str | None
    year: str | None


class OpenPrescribingDocumentPayload(TypedDict, total=False):
    identifier: str
    record: JSONMapping


class PubMedDocumentPayload(TypedDict, total=False):
    pmid: str
    pmcid: str | None
    doi: str | None
    title: str
    abstract: str
    authors: Sequence[str]
    mesh_terms: Sequence[str]
    journal: str | None
    pub_year: str | None
    pub_types: Sequence[str]
    pubdate: str | None


class PmcSectionPayload(TypedDict, total=False):
    title: str
    text: str


class PmcMediaPayload(TypedDict, total=False):
    label: str
    caption: str
    uri: str


class PmcReferencePayload(TypedDict, total=False):
    label: str
    citation: str


class PmcDocumentPayload(TypedDict, total=False):
    pmcid: str
    title: str
    abstract: str
    sections: Sequence[PmcSectionPayload]
    tables: Sequence[PmcMediaPayload]
    figures: Sequence[PmcMediaPayload]
    references: Sequence[PmcReferencePayload]


class MedRxivDocumentPayload(TypedDict, total=False):
    doi: str
    title: str
    abstract: str
    date: str | None


class MeshDocumentPayload(TypedDict, total=False):
    descriptor_id: str | None
    name: str
    terms: Sequence[str]


class UmlsDocumentPayload(TypedDict, total=False):
    cui: str | None
    name: str | None
    synonyms: Sequence[str]
    definition: str | None


class LoincDocumentPayload(TypedDict, total=False):
    code: str | None
    display: str | None
    property: JSONValue
    system: JSONValue
    method: JSONValue


class Icd11DocumentPayload(TypedDict, total=False):
    code: str | None
    title: str | None
    definition: str | None
    uri: str | None


class SnomedDocumentPayload(TypedDict, total=False):
    code: str | None
    display: str | None
    designation: Sequence[JSONMapping]


AnyDocumentPayload = Union[
    ClinicalDocumentPayload,
    OpenFdaDocumentPayload,
    DailyMedDocumentPayload,
    RxNormDocumentPayload,
    AccessGudidDocumentPayload,
    NiceGuidelineDocumentPayload,
    UspstfDocumentPayload,
    CdcSocrataDocumentPayload,
    CdcWonderDocumentPayload,
    WhoGhoDocumentPayload,
    OpenPrescribingDocumentPayload,
    PubMedDocumentPayload,
    PmcDocumentPayload,
    MedRxivDocumentPayload,
    MeshDocumentPayload,
    UmlsDocumentPayload,
    LoincDocumentPayload,
    Icd11DocumentPayload,
    SnomedDocumentPayload,
]


DocumentRaw = Union[AnyDocumentPayload, JSONValue]
