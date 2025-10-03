from __future__ import annotations

import asyncio
from pathlib import Path

import sys
import types

import pytest

# Minimal httpx stub to satisfy optional dependency checks during import time.
class _StubResponse:
    status_code = 200
    text = ""
    content = b""
    elapsed = None

    def json(self, **_: object) -> object:
        return {}

    def raise_for_status(self) -> None:
        return None


class _StubAsyncStream:
    async def __aenter__(self) -> _StubResponse:
        return _StubResponse()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: BaseException | None,
    ) -> None:
        return None


class _StubAsyncClient:
    async def request(self, method: str, url: str, **_: object) -> _StubResponse:
        return _StubResponse()

    def stream(self, method: str, url: str, **_: object) -> _StubAsyncStream:
        return _StubAsyncStream()

    async def aclose(self) -> None:
        return None


class _StubClient:
    def get(self, url: str, **_: object) -> _StubResponse:
        return _StubResponse()

    def post(self, url: str, **_: object) -> _StubResponse:
        return _StubResponse()

    def close(self) -> None:
        return None


sys.modules.setdefault(
    "httpx",
    types.SimpleNamespace(
        AsyncClient=_StubAsyncClient,
        Client=_StubClient,
        HTTPError=Exception,
        Response=_StubResponse,
        Request=object,
        TimeoutException=Exception,
    ),
)


from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.adapters.clinical import ClinicalTrialsGovAdapter
from Medical_KG.ingestion.adapters.guidelines import NiceGuidelineAdapter
from Medical_KG.ingestion.adapters.literature import MedRxivAdapter, PubMedAdapter
from Medical_KG.ingestion.ledger import IngestionLedger
from Medical_KG.ingestion.payloads import (
    ClinicalStudyPayload,
    MedRxivPayload,
    NiceGuidelinePayload,
    PubMedPayload,
)


class _DummyHttpClient:
    async def aclose(self) -> None:  # pragma: no cover - no-op for tests
        return None

    def set_rate_limit(self, host: str, limit: object) -> None:  # pragma: no cover - no-op for tests
        return None


@pytest.fixture
def http_client() -> _DummyHttpClient:
    client = _DummyHttpClient()
    try:
        yield client
    finally:
        asyncio.run(client.aclose())


@pytest.fixture
def adapter_context(tmp_path: Path) -> AdapterContext:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    return AdapterContext(ledger=ledger)


def test_clinical_adapter_emits_typed_document(
    adapter_context: AdapterContext, http_client: _DummyHttpClient
) -> None:
    payload: ClinicalStudyPayload = {
        "protocolSection": {
            "identificationModule": {"nctId": "NCT00000001", "briefTitle": "Trial"},
            "statusModule": {"overallStatus": "Recruiting"},
            "descriptionModule": {"briefSummary": "Summary"},
            "designModule": {"phases": ["Phase 1"], "studyType": "Interventional"},
            "armsInterventionsModule": {"arms": []},
            "eligibilityModule": {"eligibilityCriteria": "Adults"},
            "outcomesModule": {"primaryOutcomes": []},
        },
        "derivedSection": {"miscInfoModule": {"version": "v1"}},
    }
    adapter = ClinicalTrialsGovAdapter(adapter_context, http_client, bootstrap_records=[payload])
    results = asyncio.run(adapter.run())
    document = results[0].document
    assert document.raw is not None
    assert isinstance(document.raw, dict)
    assert document.raw["nct_id"] == "NCT00000001"
    assert document.metadata["record_version"] == "v1"


def test_clinical_adapter_validation_rejects_bad_identifier(
    adapter_context: AdapterContext, http_client: _DummyHttpClient
) -> None:
    payload: ClinicalStudyPayload = {
        "protocolSection": {
            "identificationModule": {"nctId": "BAD-ID", "briefTitle": "Trial"},
            "statusModule": {"overallStatus": "Recruiting"},
            "descriptionModule": {"briefSummary": "Summary"},
            "designModule": {"phases": ["Phase 1"], "studyType": "Interventional"},
            "armsInterventionsModule": {"arms": []},
            "eligibilityModule": {"eligibilityCriteria": "Adults"},
            "outcomesModule": {"primaryOutcomes": []},
        },
        "derivedSection": {"miscInfoModule": {"version": "v1"}},
    }
    adapter = ClinicalTrialsGovAdapter(adapter_context, http_client, bootstrap_records=[payload])
    with pytest.raises(ValueError):
        asyncio.run(adapter.run())


def test_guideline_adapter_handles_typed_payload(
    adapter_context: AdapterContext, http_client: _DummyHttpClient
) -> None:
    payload: NiceGuidelinePayload = {
        "uid": "NG100",
        "title": "Guideline",
        "summary": "Summary",
        "licence": "OpenGov",
    }
    adapter = NiceGuidelineAdapter(adapter_context, http_client, bootstrap_records=[payload])
    results = asyncio.run(adapter.run())
    document = results[0].document
    assert document.raw["uid"] == "NG100"
    assert document.metadata["licence"] == "OpenGov"


def test_guideline_adapter_rejects_invalid_licence(
    adapter_context: AdapterContext, http_client: _DummyHttpClient
) -> None:
    payload: NiceGuidelinePayload = {
        "uid": "NG101",
        "title": "Guideline",
        "summary": "Summary",
        "licence": "Proprietary",
    }
    adapter = NiceGuidelineAdapter(adapter_context, http_client, bootstrap_records=[payload])
    with pytest.raises(ValueError):
        asyncio.run(adapter.run())


def test_pubmed_parse_and_validate(adapter_context: AdapterContext, http_client: _DummyHttpClient) -> None:
    adapter = PubMedAdapter(adapter_context, http_client)
    payload: PubMedPayload = {
        "pmid": "1234567",
        "title": "Example",
        "abstract": "Body",
        "authors": [],
        "mesh_terms": [],
        "journal": "Journal",
        "pub_year": "2024",
        "pub_types": [],
        "pubdate": "2024",
        "sortpubdate": "2024",
        "fulljournalname": "Journal",
    }
    document = adapter.parse(payload)
    adapter.validate(document)
    bad_payload = payload.copy()
    bad_payload["pmid"] = "bad"
    bad_document = adapter.parse(bad_payload)
    with pytest.raises(ValueError):
        adapter.validate(bad_document)


def test_medrxiv_validate_enforces_doi(
    adapter_context: AdapterContext, http_client: _DummyHttpClient
) -> None:
    adapter = MedRxivAdapter(adapter_context, http_client)
    payload: MedRxivPayload = {
        "doi": "10.1101/2024.01.01",
        "title": "Study",
        "abstract": "Summary",
        "version": "1",
    }
    document = adapter.parse(payload)
    adapter.validate(document)
    invalid = payload.copy()
    invalid["doi"] = "invalid"
    bad_document = adapter.parse(invalid)
    with pytest.raises(ValueError):
        adapter.validate(bad_document)
