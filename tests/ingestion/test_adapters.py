import asyncio
import json
from pathlib import Path

from Medical_KG.ingestion.adapters.base import AdapterContext
from Medical_KG.ingestion.adapters.clinical import (
    AccessGudidAdapter,
    ClinicalTrialsGovAdapter,
    OpenFdaAdapter,
    RxNormAdapter,
)
from Medical_KG.ingestion.adapters.guidelines import (
    CdcSocrataAdapter,
    NiceGuidelineAdapter,
)
from Medical_KG.ingestion.adapters.literature import MedRxivAdapter, PmcAdapter, PubMedAdapter
from Medical_KG.ingestion.adapters.terminology import Icd11Adapter, LoincAdapter, MeSHAdapter, SnomedAdapter, UMLSAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.ledger import IngestionLedger


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def test_pubmed_adapter_parses_fixture(monkeypatch, tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    context = AdapterContext(ledger=ledger)
    client = AsyncHttpClient()
    adapter = PubMedAdapter(context, client, api_key=None)

    async def fake_fetch_json(url: str, *, params: dict | None = None, headers: dict | None = None) -> dict:
        if "esearch" in url:
            return json.loads(Path("tests/fixtures/ingestion/pubmed_search.json").read_text())
        return json.loads(Path("tests/fixtures/ingestion/pubmed_summary.json").read_text())

    monkeypatch.setattr(adapter, "fetch_json", fake_fetch_json)

    async def _exec() -> None:
        results = await adapter.run(term="lactate")
        assert len(results) == 1
        assert results[0].document.metadata["title"].startswith("Lactate")
        await client.aclose()

    _run(_exec())


def test_clinicaltrials_adapter_validates_nct(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    context = AdapterContext(ledger=ledger)
    client = AsyncHttpClient()
    payload = json.loads(Path("tests/fixtures/ingestion/ctgov_study.json").read_text())
    adapter = ClinicalTrialsGovAdapter(context, client, bootstrap_records=[payload])

    async def _exec() -> None:
        results = await adapter.run()
        assert results[0].document.metadata["record_version"] == "2024-01-01"
        await client.aclose()

    _run(_exec())


def test_openfda_adapter_handles_identifier(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    context = AdapterContext(ledger=ledger)
    client = AsyncHttpClient()
    payload = json.loads(Path("tests/fixtures/ingestion/openfda_faers.json").read_text())["results"][0]
    adapter = OpenFdaAdapter(context, client, bootstrap_records=[payload])

    async def _exec() -> None:
        results = await adapter.run(resource="drug/event")
        assert results[0].document.metadata["identifier"] == "R1"
        await client.aclose()

    _run(_exec())


def test_terminology_adapters(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    context = AdapterContext(ledger=ledger)
    client = AsyncHttpClient()
    mesh_payload = json.loads(Path("tests/fixtures/ingestion/mesh_descriptor.json").read_text())
    umls_payload = json.loads(Path("tests/fixtures/ingestion/umls_cui.json").read_text())
    loinc_payload = json.loads(Path("tests/fixtures/ingestion/loinc_lookup.json").read_text())
    icd_payload = json.loads(Path("tests/fixtures/ingestion/icd11_code.json").read_text())
    snomed_payload = json.loads(Path("tests/fixtures/ingestion/snomed_lookup.json").read_text())

    async def _exec() -> None:
        mesh_result = await MeSHAdapter(context, client, bootstrap_records=[mesh_payload]).run(descriptor_id="D012345")
        umls_result = await UMLSAdapter(context, client, bootstrap_records=[umls_payload]).run(cui="C1234567")
        loinc_result = await LoincAdapter(context, client, bootstrap_records=[loinc_payload]).run(code="4548-4")
        icd_result = await Icd11Adapter(context, client, bootstrap_records=[icd_payload]).run(code="1A00")
        snomed_result = await SnomedAdapter(context, client, bootstrap_records=[snomed_payload]).run(code="44054006")
        assert mesh_result[0].document.metadata["descriptor_id"] == "D012345"
        assert umls_result[0].document.metadata["cui"] == "C1234567"
        assert loinc_result[0].document.metadata["code"] == "4548-4"
        assert icd_result[0].document.metadata["code"] == "1A00"
        assert snomed_result[0].document.metadata["code"] == "44054006"
        await client.aclose()

    _run(_exec())


def test_guideline_adapters(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    context = AdapterContext(ledger=ledger)
    client = AsyncHttpClient()
    nice_payload = json.loads(Path("tests/fixtures/ingestion/nice_guideline.json").read_text())
    cdc_payload = json.loads(Path("tests/fixtures/ingestion/cdc_socrata.json").read_text())
    adapter_nice = NiceGuidelineAdapter(context, client, bootstrap_records=[nice_payload])
    adapter_cdc = CdcSocrataAdapter(context, client, bootstrap_records=cdc_payload)

    async def _exec() -> None:
        nice_result = await adapter_nice.run()
        cdc_result = await adapter_cdc.run(dataset="abc")
        assert nice_result[0].document.metadata["uid"] == "CG123"
        assert cdc_result[0].document.metadata["identifier"].startswith("CA-2023")
        await client.aclose()

    _run(_exec())


def test_accessgudid_validation(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    context = AdapterContext(ledger=ledger)
    client = AsyncHttpClient()
    payload = json.loads(Path("tests/fixtures/ingestion/accessgudid.json").read_text())
    adapter = AccessGudidAdapter(context, client, bootstrap_records=[payload])

    async def _exec() -> None:
        results = await adapter.run(udi_di="00380740000011")
        assert results[0].document.metadata["udi_di"] == "00380740000011"
        await client.aclose()

    _run(_exec())


def test_literature_adapters(tmp_path: Path) -> None:
    ledger = IngestionLedger(tmp_path / "ledger.jsonl")
    context = AdapterContext(ledger=ledger)
    client = AsyncHttpClient()
    pmc_xml = Path("tests/fixtures/ingestion/pmc_record.xml").read_text()
    medrxiv_payload = json.loads(Path("tests/fixtures/ingestion/medrxiv.json").read_text())
    pmc_adapter = PmcAdapter(context, client)
    medrxiv_adapter = MedRxivAdapter(context, client)

    async def fake_fetch_text(*_, **__):
        return f"<ListRecords>{pmc_xml}</ListRecords>"

    async def fake_fetch_json(*_, **__):
        return medrxiv_payload

    pmc_adapter.fetch_text = fake_fetch_text  # type: ignore[assignment]
    medrxiv_adapter.fetch_json = fake_fetch_json  # type: ignore[assignment]

    async def _exec() -> None:
        pmc_results = await pmc_adapter.run(set_spec="pmc")
        medrxiv_results = await medrxiv_adapter.run()
        assert pmc_results[0].document.metadata["datestamp"] == "2024-01-15"
        assert medrxiv_results[0].document.metadata["title"].startswith("Rapid")
        await client.aclose()

    _run(_exec())
