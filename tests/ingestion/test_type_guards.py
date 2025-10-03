"""Unit tests for Document.raw type guard helpers."""
from __future__ import annotations

from typing import Callable, assert_type

import pytest

import Medical_KG.ingestion.types as types


def make_mesh_payload() -> types.MeshDocumentPayload:
    return {
        "name": "Hypertension",
        "terms": ["Hypertension"],
        "descriptor_id": "D012345",
    }


def make_umls_payload() -> types.UmlsDocumentPayload:
    return {
        "synonyms": ["Hypertension"],
        "cui": "C1234567",
        "name": "Hypertension",
        "definition": "High blood pressure",
    }


def make_loinc_payload() -> types.LoincDocumentPayload:
    return {
        "property": "LP",
        "system": "Blood",
        "method": "Observation",
        "code": "1234-5",
        "display": "Blood pressure",
    }


def make_icd11_payload() -> types.Icd11DocumentPayload:
    return {
        "code": "AB12",
        "title": "Hypertension",
        "definition": "Persistent high blood pressure",
        "uri": "https://icd.who.int/1",
    }


def make_snomed_payload() -> types.SnomedDocumentPayload:
    return {
        "code": "123456",
        "display": "Hypertension",
        "designation": [{"value": "Hypertension"}],
    }


def make_clinical_document_payload() -> types.ClinicalDocumentPayload:
    return {
        "nct_id": "NCT12345678",
        "title": "Clinical study",
        "version": "v1",
        "arms": [],
        "eligibility": "Adults",
        "outcomes": [],
    }


def make_openfda_payload() -> types.OpenFdaDocumentPayload:
    return {
        "identifier": "case-1",
        "version": "1",
        "record": {},
    }


def make_dailymed_payload() -> types.DailyMedDocumentPayload:
    return {
        "setid": "abcd",
        "title": "Medication guide",
        "version": "1",
        "sections": [{"text": "Instructions"}],
    }


def make_rxnorm_payload() -> types.RxNormDocumentPayload:
    return {
        "rxcui": "12345",
    }


def make_access_gudid_payload() -> types.AccessGudidDocumentPayload:
    return {
        "udi_di": "00012345678901",
        "brand": "Device",
    }


def make_nice_guideline_payload() -> types.NiceGuidelineDocumentPayload:
    return {
        "uid": "NG1",
        "title": "Guideline",
        "summary": "Summary",
    }


def make_uspstf_payload() -> types.UspstfDocumentPayload:
    return {
        "title": "USPSTF recommendation",
        "status": "active",
        "url": "https://example.com/uspstf",
    }


def make_cdc_socrata_payload() -> types.CdcSocrataDocumentPayload:
    return {
        "identifier": "cdc-1",
        "record": {"state": "CA"},
    }


def make_cdc_wonder_payload() -> types.CdcWonderDocumentPayload:
    return {
        "rows": [{"indicator": "mortality", "value": "10"}],
    }


def make_who_gho_payload() -> types.WhoGhoDocumentPayload:
    return {
        "indicator": "LIFE_EXPECTANCY",
        "value": 72.5,
        "country": "US",
        "year": "2024",
    }


def make_openprescribing_payload() -> types.OpenPrescribingDocumentPayload:
    return {
        "identifier": "open-1",
        "record": {"practice": "A123"},
    }


def make_pubmed_payload() -> types.PubMedDocumentPayload:
    return {
        "pmid": "12345678",
        "title": "Sample publication",
        "abstract": "Abstract text",
        "authors": ["Doe"],
        "mesh_terms": ["Hypertension"],
        "pub_types": ["Journal Article"],
    }


def make_pmc_payload() -> types.PmcDocumentPayload:
    return {
        "pmcid": "PMC1234567",
        "title": "PMC article",
        "abstract": "Abstract text",
        "sections": [],
        "tables": [],
        "figures": [],
        "references": [],
    }


def make_medrxiv_payload() -> types.MedRxivDocumentPayload:
    return {
        "doi": "10.1101/123456",
        "title": "Preprint",
        "abstract": "Abstract text",
    }


@pytest.mark.parametrize(
    "factory",
    [
        make_mesh_payload,
        make_umls_payload,
        make_loinc_payload,
        make_icd11_payload,
        make_snomed_payload,
    ],
)
def test_terminology_family_guard_accepts_members(factory: Callable[[], types.TerminologyDocumentPayload]) -> None:
    payload = factory()
    assert types.is_terminology_payload(payload)


@pytest.mark.parametrize(
    "factory",
    [
        make_clinical_document_payload,
        make_openfda_payload,
        make_dailymed_payload,
        make_rxnorm_payload,
        make_access_gudid_payload,
    ],
)
def test_clinical_family_guard_accepts_members(factory: Callable[[], types.ClinicalCatalogDocumentPayload]) -> None:
    payload = factory()
    assert types.is_clinical_payload(payload)


@pytest.mark.parametrize(
    "factory",
    [make_nice_guideline_payload, make_uspstf_payload],
)
def test_guideline_family_guard_accepts_members(factory: Callable[[], types.GuidelineDocumentPayload]) -> None:
    payload = factory()
    assert types.is_guideline_payload(payload)


@pytest.mark.parametrize(
    "factory",
    [
        make_cdc_socrata_payload,
        make_cdc_wonder_payload,
        make_who_gho_payload,
        make_openprescribing_payload,
    ],
)
def test_knowledge_base_family_guard_accepts_members(factory: Callable[[], types.KnowledgeBaseDocumentPayload]) -> None:
    payload = factory()
    assert types.is_knowledge_base_payload(payload)


@pytest.mark.parametrize(
    "factory",
    [make_pubmed_payload, make_pmc_payload, make_medrxiv_payload],
)
def test_literature_family_guard_accepts_members(factory: Callable[[], types.LiteratureDocumentPayload]) -> None:
    payload = factory()
    assert types.is_literature_payload(payload)


def test_family_guards_reject_mismatched_payloads() -> None:
    mesh_payload = make_mesh_payload()
    pubmed_payload = make_pubmed_payload()
    assert not types.is_terminology_payload(pubmed_payload)
    assert not types.is_literature_payload(mesh_payload)
    assert not types.is_clinical_payload(pubmed_payload)
    assert not types.is_guideline_payload(mesh_payload)
    assert not types.is_knowledge_base_payload(pubmed_payload)
    assert not types.is_literature_payload(None)


@pytest.mark.parametrize(
    ("guard", "factory"),
    [
        (types.is_mesh_payload, make_mesh_payload),
        (types.is_umls_payload, make_umls_payload),
        (types.is_loinc_payload, make_loinc_payload),
        (types.is_icd11_payload, make_icd11_payload),
        (types.is_snomed_payload, make_snomed_payload),
        (types.is_clinical_document_payload, make_clinical_document_payload),
        (types.is_openfda_payload, make_openfda_payload),
        (types.is_dailymed_payload, make_dailymed_payload),
        (types.is_rxnorm_payload, make_rxnorm_payload),
        (types.is_access_gudid_payload, make_access_gudid_payload),
        (types.is_nice_guideline_payload, make_nice_guideline_payload),
        (types.is_uspstf_payload, make_uspstf_payload),
        (types.is_cdc_socrata_payload, make_cdc_socrata_payload),
        (types.is_cdc_wonder_payload, make_cdc_wonder_payload),
        (types.is_who_gho_payload, make_who_gho_payload),
        (types.is_openprescribing_payload, make_openprescribing_payload),
        (types.is_pubmed_payload, make_pubmed_payload),
        (types.is_pmc_payload, make_pmc_payload),
        (types.is_medrxiv_payload, make_medrxiv_payload),
    ],
)
def test_specific_guards_return_true_for_matching_payloads(
    guard: Callable[[types.DocumentRaw | None], bool],
    factory: Callable[[], types.DocumentRaw],
) -> None:
    assert guard(factory())


@pytest.mark.parametrize(
    "guard",
    [
        types.is_mesh_payload,
        types.is_umls_payload,
        types.is_loinc_payload,
        types.is_icd11_payload,
        types.is_snomed_payload,
        types.is_clinical_document_payload,
        types.is_openfda_payload,
        types.is_dailymed_payload,
        types.is_rxnorm_payload,
        types.is_access_gudid_payload,
        types.is_nice_guideline_payload,
        types.is_uspstf_payload,
        types.is_cdc_socrata_payload,
        types.is_cdc_wonder_payload,
        types.is_who_gho_payload,
        types.is_openprescribing_payload,
        types.is_pubmed_payload,
        types.is_pmc_payload,
        types.is_medrxiv_payload,
    ],
)
def test_specific_guards_reject_none_and_unrelated_payloads(
    guard: Callable[[types.DocumentRaw | None], bool],
) -> None:
    assert not guard(None)
    assert not guard(make_pubmed_payload() if guard is not types.is_pubmed_payload else make_mesh_payload())


def test_pubmed_guard_narrows_type_for_mypy() -> None:
    raw: types.DocumentRaw | None = make_pubmed_payload()
    assert types.is_pubmed_payload(raw)
    assert_type(raw, types.PubMedDocumentPayload)


def test_clinical_guard_narrows_type_for_mypy() -> None:
    raw: types.DocumentRaw | None = make_clinical_document_payload()
    assert types.is_clinical_document_payload(raw)
    assert_type(raw, types.ClinicalDocumentPayload)
