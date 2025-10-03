from __future__ import annotations

from typing import Mapping, NotRequired, Sequence, TypedDict


class ClinicalIdentificationModule(TypedDict, total=False):
    nctId: str
    briefTitle: str


class ClinicalStatusModule(TypedDict, total=False):
    overallStatus: str


class ClinicalDescriptionModule(TypedDict, total=False):
    briefSummary: str


class ClinicalDesignModule(TypedDict, total=False):
    phases: Sequence[str]
    studyType: str


class ClinicalArmsModule(TypedDict, total=False):
    arms: Sequence[Mapping[str, object]]


class ClinicalEligibilityModule(TypedDict, total=False):
    eligibilityCriteria: str


class ClinicalOutcomesModule(TypedDict, total=False):
    primaryOutcomes: Sequence[Mapping[str, object]]


class ClinicalProtocolSection(TypedDict, total=False):
    identificationModule: ClinicalIdentificationModule
    statusModule: ClinicalStatusModule
    descriptionModule: ClinicalDescriptionModule
    designModule: ClinicalDesignModule
    armsInterventionsModule: ClinicalArmsModule
    eligibilityModule: ClinicalEligibilityModule
    outcomesModule: ClinicalOutcomesModule


class ClinicalMiscInfoModule(TypedDict, total=False):
    version: str


class ClinicalDerivedSection(TypedDict, total=False):
    miscInfoModule: ClinicalMiscInfoModule


class ClinicalStudyPayload(TypedDict, total=False):
    protocolSection: ClinicalProtocolSection
    derivedSection: ClinicalDerivedSection


class ClinicalStudiesResponse(TypedDict, total=False):
    studies: Sequence[ClinicalStudyPayload]
    nextPageToken: str


class ClinicalStudyDocumentPayload(TypedDict, total=False):
    nct_id: str
    title: str
    status: NotRequired[str | None]
    phase: str
    study_type: NotRequired[str | None]
    arms: NotRequired[Sequence[Mapping[str, object]]]
    eligibility: NotRequired[str | None]
    outcomes: NotRequired[Sequence[Mapping[str, object]]]
    version: str


class OpenFdaPayload(TypedDict, total=False):
    safetyreportid: str
    udi_di: str
    setid: str
    id: str
    receivedate: str
    version_number: str
    last_updated: str
    results: Sequence[Mapping[str, object]]


class DailyMedSection(TypedDict, total=False):
    loinc: str | None
    text: str


class DailyMedDocumentPayload(TypedDict, total=False):
    setid: str
    title: str
    sections: Sequence[DailyMedSection]


class RxNormProperties(TypedDict, total=False):
    rxcui: str
    name: str
    synonym: str
    tty: str
    ndc: str


class RxNormPayload(TypedDict, total=False):
    properties: RxNormProperties


class RxNormDocumentPayload(TypedDict, total=False):
    rxcui: str
    name: NotRequired[str | None]
    synonym: NotRequired[str | None]
    tty: NotRequired[str | None]
    ndc: NotRequired[str | None]


class GudidUdiPayload(TypedDict, total=False):
    deviceIdentifier: str
    brandName: NotRequired[str]
    versionOrModelNumber: NotRequired[str]
    companyName: NotRequired[str]
    deviceDescription: NotRequired[str]


class AccessGudidPayload(TypedDict, total=False):
    udi: GudidUdiPayload
    udi_di: NotRequired[str]


class AccessGudidDocumentPayload(TypedDict, total=False):
    udi_di: str | None
    brand: NotRequired[str | None]
    model: NotRequired[str | None]
    company: NotRequired[str | None]
    description: NotRequired[str | None]


class PubMedPayload(TypedDict, total=False):
    pmid: str
    pmcid: NotRequired[str | None]
    doi: NotRequired[str | None]
    title: str
    abstract: str
    authors: NotRequired[Sequence[object]]
    mesh_terms: NotRequired[Sequence[str]]
    journal: NotRequired[str | None]
    pub_year: NotRequired[str | None]
    pub_types: NotRequired[Sequence[str]]
    pubdate: NotRequired[str | None]
    sortpubdate: NotRequired[str]
    fulljournalname: NotRequired[str]


class PmcSection(TypedDict, total=False):
    title: str
    text: str


class PmcAsset(TypedDict, total=False):
    label: str
    caption: str
    uri: str


class PmcReference(TypedDict, total=False):
    label: str
    citation: str


class PmcDocumentPayload(TypedDict, total=False):
    pmcid: str
    title: str
    abstract: str
    sections: Sequence[PmcSection]
    tables: Sequence[PmcAsset]
    figures: Sequence[PmcAsset]
    references: Sequence[PmcReference]


class MedRxivPayload(TypedDict, total=False):
    doi: str
    title: str
    abstract: str
    date: NotRequired[str]
    version: NotRequired[str]
    authors: NotRequired[Sequence[str]]


class NiceGuidelinePayload(TypedDict, total=False):
    uid: str
    title: str
    summary: str
    url: NotRequired[str]
    licence: NotRequired[str]


class UspstfPayload(TypedDict, total=False):
    id: str
    title: str
    status: NotRequired[str]
    url: NotRequired[str]


class CdcSocrataRow(TypedDict, total=False):
    row_id: str
    state: NotRequired[str]
    year: NotRequired[str]
    indicator: NotRequired[str]


class CdcWonderRow(TypedDict, total=False):
    __key: NotRequired[str]


class CdcWonderPayload(TypedDict, total=False):
    rows: Sequence[Mapping[str, str]]


class WhoGhoPayload(TypedDict, total=False):
    Indicator: str
    Value: str | None
    SpatialDim: str | None
    TimeDim: str | None


class WhoGhoDocumentPayload(TypedDict, total=False):
    indicator: str | None
    value: str | None
    country: str | None
    year: str | None


class OpenPrescribingRow(TypedDict, total=False):
    row_id: NotRequired[str]
    practice: NotRequired[str]


class TerminologyDocumentPayload(TypedDict, total=False):
    identifier: str

