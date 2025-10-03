"""Shared typing utilities for ingestion adapters."""
from __future__ import annotations

from typing import Mapping, MutableMapping, NotRequired, Sequence, TypedDict, Union


JSONPrimitive = Union[str, int, float, bool, None]
JSONValue = Union[JSONPrimitive, Mapping[str, "JSONValue"], Sequence["JSONValue"]]
JSONMapping = Mapping[str, JSONValue]
JSONSequence = Sequence[JSONValue]
MutableJSONMapping = MutableMapping[str, JSONValue]


class ClinicalTrialsStudyPayload(TypedDict):
    protocolSection: JSONMapping
    derivedSection: NotRequired[JSONMapping]


class ClinicalDocumentPayload(TypedDict):
    nct_id: str
    title: str
    version: str
    arms: Sequence[JSONMapping]
    eligibility: JSONValue
    outcomes: Sequence[JSONMapping]
    status: NotRequired[str | None]
    phase: NotRequired[str | None]
    study_type: NotRequired[str | None]
    lead_sponsor: NotRequired[str | None]
    enrollment: NotRequired[int | str | None]
    start_date: NotRequired[str | None]
    completion_date: NotRequired[str | None]


class OpenFdaRecordPayload(TypedDict, total=False):
    safetyreportid: NotRequired[str | None]
    udi_di: NotRequired[str | None]
    setid: NotRequired[str | None]
    id: NotRequired[str | None]
    receivedate: NotRequired[str | None]
    version_number: NotRequired[str | None]
    last_updated: NotRequired[str | None]


class OpenFdaDocumentPayload(TypedDict):
    identifier: str
    version: str
    record: JSONMapping


class DailyMedSectionPayload(TypedDict):
    text: str
    loinc: NotRequired[str | None]


class DailyMedDocumentPayload(TypedDict):
    setid: str
    title: str
    version: str
    sections: Sequence[DailyMedSectionPayload]


class RxNormDocumentPayload(TypedDict):
    rxcui: str
    name: NotRequired[str | None]
    synonym: NotRequired[str | None]
    tty: NotRequired[str | None]
    ndc: NotRequired[str | None]


class AccessGudidDocumentPayload(TypedDict):
    udi_di: str
    brand: NotRequired[str | None]
    model: NotRequired[str | None]
    company: NotRequired[str | None]
    description: NotRequired[str | None]


class NiceGuidelineDocumentPayload(TypedDict):
    uid: str
    title: str
    summary: str
    url: NotRequired[str | None]
    licence: NotRequired[str | None]


class UspstfDocumentPayload(TypedDict):
    title: str
    id: NotRequired[str | None]
    status: NotRequired[str | None]
    url: NotRequired[str | None]


class CdcSocrataDocumentPayload(TypedDict):
    identifier: str
    record: JSONMapping


class CdcWonderDocumentPayload(TypedDict):
    rows: Sequence[Mapping[str, str]]


class WhoGhoDocumentPayload(TypedDict):
    value: JSONValue
    indicator: NotRequired[str | None]
    country: NotRequired[str | None]
    year: NotRequired[str | None]


class OpenPrescribingDocumentPayload(TypedDict):
    identifier: str
    record: JSONMapping


class PubMedDocumentPayload(TypedDict):
    pmid: str
    title: str
    abstract: str
    authors: Sequence[str]
    mesh_terms: Sequence[str]
    pub_types: Sequence[str]
    pmcid: NotRequired[str | None]
    doi: NotRequired[str | None]
    journal: NotRequired[str | None]
    pub_year: NotRequired[str | None]
    pubdate: NotRequired[str | None]


class PmcSectionPayload(TypedDict):
    title: str
    text: str


class PmcMediaPayload(TypedDict):
    label: str
    caption: str
    uri: str


class PmcReferencePayload(TypedDict):
    label: str
    citation: str


class PmcDocumentPayload(TypedDict):
    pmcid: str
    title: str
    abstract: str
    sections: Sequence[PmcSectionPayload]
    tables: Sequence[PmcMediaPayload]
    figures: Sequence[PmcMediaPayload]
    references: Sequence[PmcReferencePayload]


class MedRxivDocumentPayload(TypedDict):
    doi: str
    title: str
    abstract: str
    date: NotRequired[str | None]


class MeshDocumentPayload(TypedDict):
    name: str
    terms: Sequence[str]
    descriptor_id: NotRequired[str | None]


class UmlsDocumentPayload(TypedDict):
    synonyms: Sequence[str]
    cui: NotRequired[str | None]
    name: NotRequired[str | None]
    definition: NotRequired[str | None]


class LoincDocumentPayload(TypedDict):
    property: JSONValue
    system: JSONValue
    method: JSONValue
    code: NotRequired[str | None]
    display: NotRequired[str | None]


class Icd11DocumentPayload(TypedDict):
    code: NotRequired[str | None]
    title: NotRequired[str | None]
    definition: NotRequired[str | None]
    uri: NotRequired[str | None]


class SnomedDocumentPayload(TypedDict):
    designation: Sequence[JSONMapping]
    code: NotRequired[str | None]
    display: NotRequired[str | None]


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
