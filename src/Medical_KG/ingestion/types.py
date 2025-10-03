"""Shared typing utilities for ingestion adapters."""
from __future__ import annotations

from typing import Mapping, MutableMapping, NotRequired, Sequence, TypedDict, Union


JSONPrimitive = Union[str, int, float, bool, None]
JSONValue = Union[JSONPrimitive, Mapping[str, "JSONValue"], Sequence["JSONValue"]]
JSONMapping = Mapping[str, JSONValue]
JSONSequence = Sequence[JSONValue]
MutableJSONMapping = MutableMapping[str, JSONValue]


# Common mixins -----------------------------------------------------------


class IdentifierMixin(TypedDict):
    """Shared identifier field for payloads that expose a canonical id."""

    identifier: str


class VersionMixin(TypedDict):
    """Shared version metadata for payload revisions."""

    version: str


class TitleMixin(TypedDict):
    """Shared human-readable title for document-centric payloads."""

    title: str


class SummaryMixin(TypedDict):
    """Shared summary field used by guideline style payloads."""

    summary: str


class RecordMixin(TypedDict):
    """Shared record container for payloads wrapping arbitrary JSON rows."""

    record: JSONMapping


class ClinicalTrialsStudyPayload(TypedDict):
    protocolSection: JSONMapping
    derivedSection: NotRequired[JSONMapping]


class ClinicalDocumentPayload(TitleMixin, VersionMixin):
    nct_id: str
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


class OpenFdaRecordPayload(TypedDict):
    safetyreportid: NotRequired[str | None]
    udi_di: NotRequired[str | None]
    setid: NotRequired[str | None]
    id: NotRequired[str | None]
    receivedate: NotRequired[str | None]
    version_number: NotRequired[str | None]
    last_updated: NotRequired[str | None]


class OpenFdaDocumentPayload(IdentifierMixin, VersionMixin, RecordMixin):
    """Structured payload for OpenFDA device records."""


class DailyMedSectionPayload(TypedDict):
    text: str
    loinc: NotRequired[str | None]


class DailyMedDocumentPayload(TitleMixin, VersionMixin):
    setid: str
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


class NiceGuidelineDocumentPayload(TitleMixin, SummaryMixin):
    uid: str
    url: NotRequired[str | None]
    licence: NotRequired[str | None]


class UspstfDocumentPayload(TitleMixin):
    id: NotRequired[str | None]
    status: NotRequired[str | None]
    url: NotRequired[str | None]


class CdcSocrataDocumentPayload(IdentifierMixin, RecordMixin):
    ...


class CdcWonderDocumentPayload(TypedDict):
    rows: Sequence[Mapping[str, str]]


class WhoGhoDocumentPayload(TypedDict):
    value: JSONValue
    indicator: NotRequired[str | None]
    country: NotRequired[str | None]
    year: NotRequired[str | None]


class OpenPrescribingDocumentPayload(IdentifierMixin, RecordMixin):
    ...


class PubMedDocumentPayload(TitleMixin):
    pmid: str
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


class PmcDocumentPayload(TitleMixin):
    pmcid: str
    abstract: str
    sections: Sequence[PmcSectionPayload]
    tables: Sequence[PmcMediaPayload]
    figures: Sequence[PmcMediaPayload]
    references: Sequence[PmcReferencePayload]


class MedRxivDocumentPayload(TitleMixin):
    doi: str
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


TerminologyDocumentPayload = Union[
    MeshDocumentPayload,
    UmlsDocumentPayload,
    LoincDocumentPayload,
    Icd11DocumentPayload,
    SnomedDocumentPayload,
]


ClinicalCatalogDocumentPayload = Union[
    ClinicalDocumentPayload,
    OpenFdaDocumentPayload,
    DailyMedDocumentPayload,
    RxNormDocumentPayload,
    AccessGudidDocumentPayload,
]


GuidelineDocumentPayload = Union[
    NiceGuidelineDocumentPayload,
    UspstfDocumentPayload,
]


KnowledgeBaseDocumentPayload = Union[
    CdcSocrataDocumentPayload,
    CdcWonderDocumentPayload,
    WhoGhoDocumentPayload,
    OpenPrescribingDocumentPayload,
]


LiteratureDocumentPayload = Union[
    PubMedDocumentPayload,
    PmcDocumentPayload,
    MedRxivDocumentPayload,
]


AdapterDocumentPayload = Union[
    TerminologyDocumentPayload,
    ClinicalCatalogDocumentPayload,
    GuidelineDocumentPayload,
    KnowledgeBaseDocumentPayload,
    LiteratureDocumentPayload,
]


DocumentRaw = AdapterDocumentPayload
