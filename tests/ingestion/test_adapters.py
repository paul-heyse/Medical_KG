from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any, Mapping, MutableMapping

import pytest

from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.adapters.clinical import (
    AccessGudidAdapter,
    ClinicalTrialsGovAdapter,
    DailyMedAdapter,
    OpenFdaAdapter,
    OpenFdaUdiAdapter,
    RxNormAdapter,
    UdiValidator,
)
from Medical_KG.ingestion.adapters.guidelines import (
    CdcSocrataAdapter,
    NiceGuidelineAdapter,
)
from Medical_KG.ingestion.adapters.literature import MedRxivAdapter, PmcAdapter, PubMedAdapter
from Medical_KG.ingestion.adapters.terminology import (
    Icd11Adapter,
    LoincAdapter,
    MeSHAdapter,
    SnomedAdapter,
    UMLSAdapter,
)
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.models import Document

from tests.ingestion.fixtures.clinical import (
    accessgudid_record,
    clinical_study,
    clinical_study_without_outcomes,
    dailymed_xml,
    openfda_faers_record,
    openfda_udi_record,
)
from tests.ingestion.fixtures.guidelines import cdc_socrata_record, nice_guideline
from tests.ingestion.fixtures.literature import (
    medrxiv_record,
    pmc_record_xml,
    pubmed_fetch_xml,
    pubmed_search_payload,
    pubmed_search_without_history,
    pubmed_summary_payload,
)
from tests.ingestion.fixtures.terminology import (
    icd11_record,
    loinc_record,
    mesh_descriptor,
    rxnav_properties,
    snomed_record,
    umls_record,
)


@pytest.mark.asyncio
async def test_pubmed_adapter_fetches_batch(fake_ledger: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    client = AsyncHttpClient()
    adapter = PubMedAdapter(AdapterContext(ledger=fake_ledger), client, api_key=None)

    search_payload = pubmed_search_payload()
    summary_payload = pubmed_summary_payload()
    fetch_payload = pubmed_fetch_xml()

    async def fake_fetch_json(url: str, *, params: Mapping[str, object] | None = None, headers: Mapping[str, str] | None = None) -> dict[str, Any]:  # noqa: ANN001
        if "esearch" in url:
            return search_payload
        return summary_payload

    async def fake_fetch_text(url: str, *, params: Mapping[str, object] | None = None, headers: Mapping[str, str] | None = None) -> str:  # noqa: ANN001
        assert "efetch" in url
        return fetch_payload

    monkeypatch.setattr(adapter, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(adapter, "fetch_text", fake_fetch_text)

    results = await adapter.run(term="sepsis", retmax=10)
    assert len(results) == 1
    doc = results[0].document
    assert doc.metadata["pmid"] == "12345678"
    assert "mesh_terms" in doc.raw
    await client.aclose()


@pytest.mark.asyncio
async def test_pubmed_adapter_without_history(monkeypatch: pytest.MonkeyPatch, fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    adapter = PubMedAdapter(AdapterContext(ledger=fake_ledger), client)

    search_payload = pubmed_search_without_history()
    summary_payload = pubmed_summary_payload()
    fetch_payload = pubmed_fetch_xml()

    async def fake_fetch_json(url: str, *, params: Mapping[str, object] | None = None, headers: Mapping[str, str] | None = None) -> dict[str, Any]:  # noqa: ANN001
        if "esearch" in url:
            return search_payload
        return summary_payload

    async def fake_fetch_text(url: str, *, params: Mapping[str, object] | None = None, headers: Mapping[str, str] | None = None) -> str:  # noqa: ANN001
        return fetch_payload

    monkeypatch.setattr(adapter, "fetch_json", fake_fetch_json)
    monkeypatch.setattr(adapter, "fetch_text", fake_fetch_text)

    results = await adapter.run(term="oncology")
    assert results
    assert all(result.document.source == "pubmed" for result in results)
    await client.aclose()


def test_pubmed_rate_limit_adjusts_for_api_key(fake_ledger: Any) -> None:
    adapter_no_key = PubMedAdapter(AdapterContext(fake_ledger), AsyncHttpClient())
    adapter_with_key = PubMedAdapter(AdapterContext(fake_ledger), AsyncHttpClient(), api_key="secret")
    host = "eutils.ncbi.nlm.nih.gov"
    assert adapter_no_key.client._limits[host].rate == 3
    assert adapter_with_key.client._limits[host].rate == 10
    asyncio.run(adapter_no_key.client.aclose())
    asyncio.run(adapter_with_key.client.aclose())


@pytest.mark.asyncio
async def test_clinical_trials_parses_metadata(fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    adapter = ClinicalTrialsGovAdapter(AdapterContext(ledger=fake_ledger), client, bootstrap_records=[clinical_study()])
    results = await adapter.run()
    assert len(results) == 1
    doc = results[0].document
    assert doc.metadata["record_version"] == "2024-01-01"
    assert "study_type" in doc.raw
    await client.aclose()


@pytest.mark.asyncio
async def test_clinical_trials_handles_partial_payload(fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    adapter = ClinicalTrialsGovAdapter(
        AdapterContext(ledger=fake_ledger),
        client,
        bootstrap_records=[clinical_study_without_outcomes()],
    )
    results = await adapter.run()
    doc = results[0].document
    assert doc.raw["outcomes"] is None
    await client.aclose()


def test_clinical_trials_validate_rejects_invalid(fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    adapter = ClinicalTrialsGovAdapter(AdapterContext(fake_ledger), client)
    document = adapter.parse(clinical_study())
    document.raw["nct_id"] = "BAD"
    with pytest.raises(ValueError):
        adapter.validate(document)
    asyncio.run(client.aclose())


@pytest.mark.asyncio
async def test_clinical_trials_paginates(monkeypatch: pytest.MonkeyPatch, fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    adapter = ClinicalTrialsGovAdapter(AdapterContext(ledger=fake_ledger), client)

    calls: list[Mapping[str, object]] = []

    async def fake_fetch_json(url: str, *, params: MutableMapping[str, object] | None = None, headers: Mapping[str, str] | None = None) -> dict[str, Any]:  # noqa: ANN001
        assert params is not None
        calls.append(dict(params))
        if "pageToken" in params:
            return {"studies": [{"protocolSection": {"identificationModule": {"nctId": "NCT00000002"}}}]}
        return {
            "studies": [{"protocolSection": {"identificationModule": {"nctId": "NCT00000001"}}}],
            "nextPageToken": "token",
        }

    monkeypatch.setattr(adapter, "fetch_json", fake_fetch_json)

    async def collect() -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        async for record in adapter.fetch():
            records.append(record)
        return records

    records = await collect()
    assert [record["protocolSection"]["identificationModule"]["nctId"] for record in records] == [
        "NCT00000001",
        "NCT00000002",
    ]
    assert len(calls) == 2
    await client.aclose()


def test_udi_validator_checks_digits() -> None:
    assert UdiValidator.validate("00380740000011") is True
    assert UdiValidator.validate("12345678901234") is False


@pytest.mark.asyncio
async def test_openfda_adapter_requires_identifier(fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    adapter = OpenFdaAdapter(AdapterContext(fake_ledger), client, bootstrap_records=[{"foo": "bar"}])
    with pytest.raises(ValueError):
        await adapter.run(resource="drug/event")
    await client.aclose()


@pytest.mark.asyncio
async def test_openfda_adapter_parses_identifier(fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    adapter = OpenFdaAdapter(
        AdapterContext(fake_ledger),
        client,
        bootstrap_records=[openfda_faers_record()],
    )
    results = await adapter.run(resource="drug/event")
    assert results[0].document.metadata["identifier"]
    await client.aclose()


@pytest.mark.asyncio
async def test_openfda_udi_enriches_metadata(fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    adapter = OpenFdaUdiAdapter(AdapterContext(fake_ledger), client, bootstrap_records=[openfda_udi_record()])
    results = await adapter.run(resource="device/udi")
    metadata = results[0].document.metadata
    assert metadata["identifier"]
    assert metadata["udi_di"].isdigit()
    await client.aclose()


@pytest.mark.asyncio
async def test_accessgudid_validation_failure(fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    payload = accessgudid_record()
    payload["udi"]["deviceIdentifier"] = "1234"
    adapter = AccessGudidAdapter(AdapterContext(fake_ledger), client, bootstrap_records=[payload])
    with pytest.raises(ValueError):
        await adapter.run(udi_di="1234")
    await client.aclose()


@pytest.mark.asyncio
async def test_dailymed_parses_sections(fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    xml = dailymed_xml()
    adapter = DailyMedAdapter(AdapterContext(fake_ledger), client, bootstrap_records=[xml])
    results = await adapter.run(setid="abc")
    sections = results[0].document.raw["sections"]
    assert sections
    await client.aclose()


@pytest.mark.asyncio
async def test_pmc_adapter_collects_tables(monkeypatch: pytest.MonkeyPatch, fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    adapter = PmcAdapter(AdapterContext(fake_ledger), client)

    async def fake_fetch_text(*_: object, **__: object) -> str:
        return f"<OAI>{pmc_record_xml()}</OAI>"

    monkeypatch.setattr(adapter, "fetch_text", fake_fetch_text)
    results = await adapter.run(set_spec="pmc")
    doc = results[0].document
    assert any(table["label"] for table in doc.raw["tables"])
    await client.aclose()


@pytest.mark.asyncio
async def test_medrxiv_paginates(monkeypatch: pytest.MonkeyPatch, fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    adapter = MedRxivAdapter(AdapterContext(fake_ledger), client)

    async def fake_fetch_json(*_: object, **__: object) -> dict[str, Any]:
        if not getattr(fake_fetch_json, "called", False):
            fake_fetch_json.called = True
            return {"results": [medrxiv_record()], "next_cursor": "next"}
        return {"results": [medrxiv_record()], "next_cursor": None}

    fake_fetch_json.called = False
    monkeypatch.setattr(adapter, "fetch_json", fake_fetch_json)

    results = await adapter.run()
    assert len(results) == 2
    await client.aclose()


@pytest.mark.asyncio
async def test_guideline_adapters(fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    nice = NiceGuidelineAdapter(AdapterContext(fake_ledger), client, bootstrap_records=[nice_guideline()])
    cdc = CdcSocrataAdapter(AdapterContext(fake_ledger), client, bootstrap_records=cdc_socrata_record())
    nice_results = await nice.run()
    cdc_results = await cdc.run(dataset="abc")
    assert nice_results[0].document.metadata["uid"].startswith("CG")
    assert cdc_results[0].document.metadata["identifier"].startswith("CA-")
    await client.aclose()


@pytest.mark.asyncio
async def test_terminology_adapters_parse(fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    context = AdapterContext(fake_ledger)
    mesh = MeSHAdapter(context, client, bootstrap_records=[mesh_descriptor()])
    umls = UMLSAdapter(context, client, bootstrap_records=[umls_record()])
    loinc = LoincAdapter(context, client, bootstrap_records=[loinc_record()])
    icd = Icd11Adapter(context, client, bootstrap_records=[icd11_record()])
    snomed = SnomedAdapter(context, client, bootstrap_records=[snomed_record()])
    rxnorm = RxNormAdapter(context, client, bootstrap_records=[rxnav_properties()])

    mesh_res, umls_res, loinc_res, icd_res, snomed_res, rx_res = await asyncio.gather(
        mesh.run(descriptor_id="D012345"),
        umls.run(cui="C1234567"),
        loinc.run(code="4548-4"),
        icd.run(code="1A00"),
        snomed.run(code="44054006"),
        rxnorm.run(rxcui="12345"),
    )

    assert mesh_res[0].document.metadata["descriptor_id"].startswith("D")
    assert umls_res[0].document.metadata["cui"].startswith("C")
    assert loinc_res[0].document.metadata["code"].endswith("-4")
    assert icd_res[0].document.metadata["code"].startswith("1")
    assert snomed_res[0].document.metadata["code"].isdigit()
    assert rx_res[0].document.metadata["rxcui"].isdigit()
    await client.aclose()


def test_terminology_validations_raise(fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    context = AdapterContext(fake_ledger)
    mesh = MeSHAdapter(context, client, bootstrap_records=[mesh_descriptor()])
    umls = UMLSAdapter(context, client, bootstrap_records=[umls_record()])
    loinc = LoincAdapter(context, client, bootstrap_records=[loinc_record()])
    icd = Icd11Adapter(context, client, bootstrap_records=[icd11_record()])
    snomed = SnomedAdapter(context, client, bootstrap_records=[snomed_record()])

    document = Document("doc", "mesh", "", metadata={"descriptor_id": "BAD"}, raw={})
    with pytest.raises(ValueError):
        mesh.validate(document)

    document.metadata = {"cui": "BAD"}
    with pytest.raises(ValueError):
        umls.validate(document)

    document.metadata = {"code": "BAD"}
    with pytest.raises(ValueError):
        loinc.validate(document)

    with pytest.raises(ValueError):
        icd.validate(document)

    with pytest.raises(ValueError):
        snomed.validate(Document("doc", "snomed", "", metadata={"code": "12"}, raw={"designation": []}))

    asyncio.run(client.aclose())


class _FailingAdapter(BaseAdapter):
    source = "fail"

    async def fetch(self, *_: Any, **__: Any) -> AsyncIterator[Mapping[str, Any]]:
        yield {"id": "1"}

    def parse(self, raw: Mapping[str, Any]) -> Document:
        return Document("doc-1", self.source, "", metadata={}, raw=raw)

    def validate(self, document: Document) -> None:  # noqa: D401
        raise RuntimeError("boom")


class _SuccessfulAdapter(BaseAdapter):
    source = "success"

    async def fetch(self, *_: Any, **__: Any) -> AsyncIterator[Mapping[str, Any]]:
        yield {"id": "7"}

    def parse(self, raw: Mapping[str, Any]) -> Document:
        return Document("doc-7", self.source, "payload", metadata={"source": self.source}, raw=raw)

    def validate(self, document: Document) -> None:
        assert document.metadata["source"] == self.source


@pytest.mark.asyncio
async def test_base_adapter_records_failures(fake_ledger: Any) -> None:
    adapter = _FailingAdapter(AdapterContext(fake_ledger))
    with pytest.raises(RuntimeError):
        await adapter.run()
    entry = fake_ledger.get("doc-1")
    assert entry is not None and entry.state == "auto_failed"
    assert "boom" in entry.metadata.get("error", "")


@pytest.mark.asyncio
async def test_base_adapter_records_success(fake_ledger: Any) -> None:
    adapter = _SuccessfulAdapter(AdapterContext(fake_ledger))
    results = await adapter.run()
    assert results and results[0].document.doc_id == "doc-7"
    entry = fake_ledger.get("doc-7")
    assert entry is not None and entry.state == "auto_done"
