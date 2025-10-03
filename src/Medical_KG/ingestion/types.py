"""Shared typing utilities for ingestion adapters."""
from __future__ import annotations

from typing import Any, Mapping, MutableMapping, NotRequired, Sequence, TypeGuard, TypedDict, Union


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
    status: NotRequired[str | None]
    phase: NotRequired[str | None]
    study_type: NotRequired[str | None]
    lead_sponsor: NotRequired[str | None]
    enrollment: NotRequired[int | str | None]
    start_date: NotRequired[str | None]
    completion_date: NotRequired[str | None]
    outcomes: NotRequired[Sequence[JSONMapping]]


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


def _is_payload_dict(raw: DocumentRaw | None) -> TypeGuard[dict[str, Any]]:
    return isinstance(raw, dict)


def is_mesh_payload(raw: DocumentRaw | None) -> TypeGuard[MeshDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "terms" in raw and "descriptor_id" in raw


def is_umls_payload(raw: DocumentRaw | None) -> TypeGuard[UmlsDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "synonyms" in raw and "cui" in raw


def is_loinc_payload(raw: DocumentRaw | None) -> TypeGuard[LoincDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "property" in raw and "system" in raw and "method" in raw


def is_icd11_payload(raw: DocumentRaw | None) -> TypeGuard[Icd11DocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "code" in raw and "uri" in raw


def is_snomed_payload(raw: DocumentRaw | None) -> TypeGuard[SnomedDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "designation" in raw and "code" in raw


def is_terminology_payload(raw: DocumentRaw | None) -> TypeGuard[TerminologyDocumentPayload]:
    return bool(
        is_mesh_payload(raw)
        or is_umls_payload(raw)
        or is_loinc_payload(raw)
        or is_icd11_payload(raw)
        or is_snomed_payload(raw)
    )


def is_clinical_document_payload(raw: DocumentRaw | None) -> TypeGuard[ClinicalDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "nct_id" in raw and "arms" in raw and "eligibility" in raw


def is_openfda_payload(raw: DocumentRaw | None) -> TypeGuard[OpenFdaDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "identifier" in raw and "version" in raw and "record" in raw


def is_dailymed_payload(raw: DocumentRaw | None) -> TypeGuard[DailyMedDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "setid" in raw and "sections" in raw


def is_rxnorm_payload(raw: DocumentRaw | None) -> TypeGuard[RxNormDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "rxcui" in raw


def is_access_gudid_payload(raw: DocumentRaw | None) -> TypeGuard[AccessGudidDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "udi_di" in raw


def is_clinical_payload(raw: DocumentRaw | None) -> TypeGuard[ClinicalCatalogDocumentPayload]:
    return bool(
        is_clinical_document_payload(raw)
        or is_openfda_payload(raw)
        or is_dailymed_payload(raw)
        or is_rxnorm_payload(raw)
        or is_access_gudid_payload(raw)
    )


def is_nice_guideline_payload(raw: DocumentRaw | None) -> TypeGuard[NiceGuidelineDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "uid" in raw and "summary" in raw


def is_uspstf_payload(raw: DocumentRaw | None) -> TypeGuard[UspstfDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "title" in raw and "status" in raw


def is_guideline_payload(raw: DocumentRaw | None) -> TypeGuard[GuidelineDocumentPayload]:
    return bool(is_nice_guideline_payload(raw) or is_uspstf_payload(raw))


def is_cdc_socrata_payload(raw: DocumentRaw | None) -> TypeGuard[CdcSocrataDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "identifier" in raw and "record" in raw and "version" not in raw


def is_cdc_wonder_payload(raw: DocumentRaw | None) -> TypeGuard[CdcWonderDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "rows" in raw


def is_who_gho_payload(raw: DocumentRaw | None) -> TypeGuard[WhoGhoDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "indicator" in raw and "value" in raw


def is_openprescribing_payload(raw: DocumentRaw | None) -> TypeGuard[OpenPrescribingDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "identifier" in raw and "record" in raw and "version" not in raw


def is_knowledge_base_payload(raw: DocumentRaw | None) -> TypeGuard[KnowledgeBaseDocumentPayload]:
    return bool(
        is_cdc_socrata_payload(raw)
        or is_cdc_wonder_payload(raw)
        or is_who_gho_payload(raw)
        or is_openprescribing_payload(raw)
    )


def is_pubmed_payload(raw: DocumentRaw | None) -> TypeGuard[PubMedDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "pmid" in raw and "abstract" in raw and "authors" in raw


def is_pmc_payload(raw: DocumentRaw | None) -> TypeGuard[PmcDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "pmcid" in raw and "sections" in raw and "references" in raw


def is_medrxiv_payload(raw: DocumentRaw | None) -> TypeGuard[MedRxivDocumentPayload]:
    if not _is_payload_dict(raw):
        return False
    return "doi" in raw and "abstract" in raw


def is_literature_payload(raw: DocumentRaw | None) -> TypeGuard[LiteratureDocumentPayload]:
    return bool(is_pubmed_payload(raw) or is_pmc_payload(raw) or is_medrxiv_payload(raw))
