from __future__ import annotations

import asyncio
import copy
import json
from typing import Any, AsyncIterator, Awaitable, TypeVar

import httpx
import pytest

from Medical_KG.ingestion.adapters.clinical import (
    AccessGudidAdapter,
    ClinicalTrialsGovAdapter,
    DailyMedAdapter,
    OpenFdaAdapter,
    RxNormAdapter,
)
from Medical_KG.ingestion.adapters.guidelines import (
    CdcSocrataAdapter,
    CdcWonderAdapter,
    NiceGuidelineAdapter,
    OpenPrescribingAdapter,
    WhoGhoAdapter,
)
from Medical_KG.ingestion.adapters.literature import MedRxivAdapter, PmcAdapter, PubMedAdapter
from Medical_KG.ingestion.adapters.terminology import Icd11Adapter, LoincAdapter, MeSHAdapter, SnomedAdapter, UMLSAdapter
from Medical_KG.ingestion.http_client import AsyncHttpClient, RateLimit
from .fixtures import (
    FakeLedger,
    build_mock_transport,
    load_json_fixture,
    load_text_fixture,
    make_adapter_context,
)

T = TypeVar("T")


def _run(coro: Awaitable[T]) -> T:
    return asyncio.run(coro)


def _collect(iterator: AsyncIterator[T]) -> list[T]:
    async def _gather() -> list[T]:
        items: list[T] = []
        async for item in iterator:
            items.append(item)
        return items

    return asyncio.run(_gather())


def test_clinicaltrials_parses_complete_record() -> None:
    record = load_json_fixture("ctgov_study.json")
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = ClinicalTrialsGovAdapter(context, client, bootstrap_records=[record])
    try:
        results = _run(adapter.run())
    finally:
        _run(client.aclose())
    assert len(results) == 1
    result = results[0]
    assert result.document.metadata["record_version"] == "2024-01-01"
    assert "auto_done" == ledger.entries(state="auto_done")[0].state
    assert result.document.raw["nct_id"] == "NCT01234567"
    assert result.document.metadata["title"] == "Study of Lactate"
    assert result.document.raw["phase"] == "Phase 2"
    assert result.document.raw["study_type"] == "Interventional"
    assert result.document.raw["outcomes"][0]["measure"] == "Mortality"


def test_clinicaltrials_handles_partial_payload() -> None:
    record = load_json_fixture("ctgov_study.json")
    minimal = copy.deepcopy(record)
    minimal["protocolSection"].pop("armsInterventionsModule", None)
    minimal["protocolSection"].pop("outcomesModule", None)
    minimal["protocolSection"].pop("eligibilityModule", None)
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = ClinicalTrialsGovAdapter(context, client, bootstrap_records=[minimal])
    try:
        results = _run(adapter.run())
    finally:
        _run(client.aclose())
    document = results[0].document
    assert document.raw["arms"] == []
    assert document.raw["outcomes"] == []
    assert document.metadata["title"] == "Study of Lactate"
    assert document.content == "A study on lactate clearance."


def test_clinicaltrials_records_validation_failures() -> None:
    record = load_json_fixture("ctgov_study.json")
    invalid = copy.deepcopy(record)
    invalid["protocolSection"]["identificationModule"]["nctId"] = "INVALID"
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = ClinicalTrialsGovAdapter(context, client, bootstrap_records=[invalid])
    with pytest.raises(ValueError):
        try:
            _run(adapter.run())
        finally:
            _run(client.aclose())
    failed = list(ledger.entries(state="auto_failed"))
    assert failed
    assert "Invalid NCT ID" in failed[0].metadata["error"]


def test_clinicaltrials_records_http_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    record = load_json_fixture("ctgov_study.json")
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = ClinicalTrialsGovAdapter(context, client, bootstrap_records=[record])
    request = httpx.Request("GET", "https://clinicaltrials.gov/api/v2/studies")
    response = httpx.Response(status_code=429, request=request)

    def _raise(_: Any) -> Any:
        raise httpx.HTTPStatusError("rate limited", request=request, response=response)

    monkeypatch.setattr(adapter, "parse", _raise)
    with pytest.raises(httpx.HTTPStatusError):
        try:
            _run(adapter.run())
        finally:
            _run(client.aclose())
    failed = list(ledger.entries(state="auto_failed"))
    assert failed and "rate limited" in failed[0].metadata["error"]


def test_clinicaltrials_paginates_over_results(monkeypatch: pytest.MonkeyPatch) -> None:
    first = load_json_fixture("ctgov_study.json")
    second = copy.deepcopy(first)
    second["protocolSection"]["identificationModule"]["nctId"] = "NCT76543210"
    payloads = [
        {"studies": [first], "nextPageToken": "token"},
        {"studies": [second]},
    ]
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = ClinicalTrialsGovAdapter(context, client)

    async def _fake_fetch_json(_url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
        return payloads.pop(0)

    monkeypatch.setattr(adapter, "fetch_json", _fake_fetch_json)
    try:
        results = _run(adapter.run())
    finally:
        _run(client.aclose())
    assert [res.document.raw["nct_id"] for res in results] == ["NCT01234567", "NCT76543210"]


def test_openfda_adapter_records_identifier() -> None:
    payload = load_json_fixture("openfda_faers.json")["results"][0]
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = OpenFdaAdapter(context, client, bootstrap_records=[payload])
    try:
        results = _run(adapter.run(resource="drug/event"))
    finally:
        _run(client.aclose())
    assert results[0].document.metadata["identifier"] == "R1"


def test_dailymed_parses_sections() -> None:
    xml = load_text_fixture("dailymed_spl.xml")
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = DailyMedAdapter(context, client, bootstrap_records=[xml])
    try:
        results = _run(adapter.run(setid="abc"))
    finally:
        _run(client.aclose())
    document = results[0].document
    assert document.metadata["setid"] == "11111111-2222-3333-4444-555555555555"
    assert isinstance(document.raw["sections"], list)


def test_pubmed_adapter_uses_history_when_available(monkeypatch: pytest.MonkeyPatch) -> None:
    search_payload = load_json_fixture("pubmed_search.json")
    summary_payload = load_json_fixture("pubmed_summary.json")
    fetch_xml = load_text_fixture("pubmed_fetch.xml")
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = PubMedAdapter(context, client)
    calls: dict[str, int] = {"search": 0, "summary": 0, "fetch": 0}

    async def _fetch_json(url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
        if "esearch" in url:
            calls["search"] += 1
            return search_payload
        calls["summary"] += 1
        return summary_payload

    async def _fetch_text(url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> str:
        calls["fetch"] += 1
        return fetch_xml

    monkeypatch.setattr(adapter, "fetch_json", _fetch_json)
    monkeypatch.setattr(adapter, "fetch_text", _fetch_text)
    try:
        results = _run(adapter.run(term="lactate", retmax=1))
    finally:
        _run(client.aclose())
    assert calls == {"search": 1, "summary": 1, "fetch": 1}
    assert results[0].document.metadata["pmid"] == "12345678"


def test_pubmed_adapter_fallback_without_history(monkeypatch: pytest.MonkeyPatch) -> None:
    search_payload = load_json_fixture("pubmed_search.json")
    search_payload["esearchresult"].pop("webenv", None)
    search_payload["esearchresult"].pop("querykey", None)
    summary_payload = load_json_fixture("pubmed_summary.json")
    fetch_xml = load_text_fixture("pubmed_fetch.xml")
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = PubMedAdapter(context, client)

    async def _fetch_json(url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
        if "esearch" in url:
            return search_payload
        return summary_payload

    async def _fetch_text(url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> str:
        return fetch_xml

    monkeypatch.setattr(adapter, "fetch_json", _fetch_json)
    monkeypatch.setattr(adapter, "fetch_text", _fetch_text)
    try:
        results = _run(adapter.run(term="lactate", retmax=1))
    finally:
        _run(client.aclose())
    assert results[0].document.metadata["pmid"] == "12345678"
    assert "mesh_terms" in results[0].document.raw


def test_pubmed_adapter_adjusts_rate_limit() -> None:
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client_default = AsyncHttpClient()
    client_with_key = AsyncHttpClient()
    adapter_without_key = PubMedAdapter(context, client_default)
    adapter_with_key = PubMedAdapter(context, client_with_key, api_key="token")
    host = "eutils.ncbi.nlm.nih.gov"
    assert adapter_without_key.client._limits[host].rate == 3
    assert adapter_with_key.client._limits[host].rate == 10
    _run(adapter_with_key.client.aclose())
    _run(adapter_without_key.client.aclose())


def test_pmc_adapter_parses_sections(monkeypatch: pytest.MonkeyPatch) -> None:
    record_xml = load_text_fixture("pmc_record.xml")
    payload = f"<OAI-PMH><ListRecords>{record_xml}</ListRecords></OAI-PMH>"
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = PmcAdapter(context, client)

    async def _fetch_text(*_: Any, **__: Any) -> str:
        return payload

    monkeypatch.setattr(adapter, "fetch_text", _fetch_text)
    try:
        results = _run(adapter.run(set_spec="pmc"))
    finally:
        _run(client.aclose())
    document = results[0].document
    assert document.metadata["pmcid"].startswith("PMC")
    assert isinstance(document.raw["sections"], list)


def test_medrxiv_adapter_handles_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    first = load_json_fixture("medrxiv.json")
    second = copy.deepcopy(first)
    second["results"][0]["doi"] = "10.1101/2024.02.02.765432"
    payloads = [dict(first, next_cursor="cursor"), second]
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = MedRxivAdapter(context, client)

    async def _fetch_json(_url: str, *, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> dict[str, Any]:
        return payloads.pop(0)

    monkeypatch.setattr(adapter, "fetch_json", _fetch_json)
    try:
        results = _run(adapter.run())
    finally:
        _run(client.aclose())
    dois = {res.document.raw["doi"] for res in results}
    assert dois == {"10.1101/2024.01.01.123456", "10.1101/2024.02.02.765432"}
    assert any(res.document.metadata["authors"] for res in results)


def test_guideline_adapter_validates_metadata() -> None:
    nice_payload = load_json_fixture("nice_guideline.json")
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = NiceGuidelineAdapter(context, client, bootstrap_records=[nice_payload])
    try:
        results = _run(adapter.run())
    finally:
        _run(client.aclose())
    document = results[0].document
    assert document.metadata["uid"] == "CG123"
    assert document.metadata["licence"] == "OpenGov"


def test_guideline_adapter_rejects_invalid_licence() -> None:
    payload = load_json_fixture("nice_guideline.json")
    payload["licence"] = "Other"
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = NiceGuidelineAdapter(context, client, bootstrap_records=[payload])
    with pytest.raises(ValueError):
        try:
            _run(adapter.run())
        finally:
            _run(client.aclose())


def test_cdc_socrata_builds_identifier() -> None:
    payload = load_json_fixture("cdc_socrata.json")[0]
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = CdcSocrataAdapter(context, client, bootstrap_records=[payload])
    try:
        results = _run(adapter.run(dataset="fake"))
    finally:
        _run(client.aclose())
    assert results[0].document.metadata["identifier"].startswith("CA-2023")


def test_terminology_adapters_validate_codes() -> None:
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    mesh_payload = load_json_fixture("mesh_descriptor.json")
    umls_payload = load_json_fixture("umls_cui.json")
    loinc_payload = load_json_fixture("loinc_lookup.json")
    icd_payload = load_json_fixture("icd11_code.json")
    snomed_payload = load_json_fixture("snomed_lookup.json")
    try:
        mesh_result = _run(
            MeSHAdapter(context, client, bootstrap_records=[mesh_payload]).run(descriptor_id="D012345")
        )
        umls_result = _run(
            UMLSAdapter(context, client, bootstrap_records=[umls_payload]).run(cui="C1234567")
        )
        loinc_result = _run(
            LoincAdapter(context, client, bootstrap_records=[loinc_payload]).run(code="4548-4")
        )
        icd_result = _run(
            Icd11Adapter(context, client, bootstrap_records=[icd_payload]).run(code="1A00")
        )
        snomed_result = _run(
            SnomedAdapter(context, client, bootstrap_records=[snomed_payload]).run(code="44054006")
        )
    finally:
        _run(client.aclose())
    assert mesh_result[0].document.metadata["descriptor_id"] == "D012345"
    assert umls_result[0].document.metadata["cui"] == "C1234567"
    assert loinc_result[0].document.metadata["code"] == "4548-4"
    assert icd_result[0].document.metadata["code"] == "1A00"
    assert snomed_result[0].document.metadata["code"] == "44054006"


def test_terminology_adapter_caches_repeat_requests(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = load_json_fixture("umls_cui.json")
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    call_count = 0

    async def fake_get_json(url: str, *, params: Any | None = None, headers: Any | None = None) -> Any:
        nonlocal call_count
        call_count += 1
        return payload

    monkeypatch.setattr(client, "get_json", fake_get_json)
    adapter = UMLSAdapter(context, client)
    try:
        first = _run(adapter.run(cui="C1234567"))
        second = _run(adapter.run(cui="C1234567"))
    finally:
        _run(client.aclose())

    assert call_count == 1
    assert first[0].document.doc_id == second[0].document.doc_id
    assert len(list(ledger.entries())) == 2  # inflight + done from first run only


def test_rxnorm_adapter_enforces_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = load_json_fixture("rxnav_properties.json")
    payload["properties"]["rxcui"] = None
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = RxNormAdapter(context, client, bootstrap_records=[payload])
    with pytest.raises(ValueError):
        try:
            _run(adapter.run(rxcui="12345"))
        finally:
            _run(client.aclose())


def test_accessgudid_adapter_validates_identifier() -> None:
    payload = load_json_fixture("accessgudid.json")
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = AccessGudidAdapter(context, client, bootstrap_records=[payload])
    try:
        results = _run(adapter.run(udi_di="00380740000011"))
    finally:
        _run(client.aclose())
    assert results[0].document.metadata["udi_di"] == "00380740000011"


def test_build_mock_transport_sequences_responses() -> None:
    responses = [
        httpx.Response(status_code=200, json={"first": True}),
        httpx.Response(status_code=200, json={"second": True}),
    ]
    transport = build_mock_transport(responses)
    with httpx.Client(transport=transport) as client:
        assert client.get("https://example.com").json() == {"first": True}
        assert client.get("https://example.com").json() == {"second": True}


def test_rate_limit_factory_controls_host(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient(limits={"example.com": RateLimit(rate=1, per=1.0)})
    adapter = OpenFdaAdapter(context, client)
    responses = [httpx.Response(status_code=200, json={"results": [{"id": "1", "setid": "1"}]})]
    transport = build_mock_transport(responses)
    async_client = httpx.AsyncClient(transport=transport)
    monkeypatch.setattr(adapter.client, "_client", async_client, raising=False)
    try:
        results = _run(adapter.run(resource="drug/event"))
    finally:
        _run(adapter.client.aclose())
    assert results[0].document.metadata["identifier"] == "1"


def test_clinical_fetch_handles_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = ClinicalTrialsGovAdapter(context, client)
    pages = [
        {"studies": [{"id": 1}], "nextPageToken": "token"},
        {"studies": [{"id": 2}], "nextPageToken": None},
    ]

    async def fake_fetch_json(url: str, *, params: Any | None = None, headers: Any | None = None) -> Any:
        return pages.pop(0)

    monkeypatch.setattr(adapter, "fetch_json", fake_fetch_json)
    try:
        records = _collect(adapter.fetch())
    finally:
        _run(client.aclose())
    assert [record["id"] for record in records] == [1, 2]


def test_openfda_fetch_emits_results(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = OpenFdaAdapter(context, client, api_key="demo")
    captured: list[dict[str, Any]] = []

    async def fake_fetch_json(url: str, *, params: Any | None = None, headers: Any | None = None) -> Any:
        captured.append(dict(params or {}))
        return {"results": [{"id": "a"}, {"id": "b"}]}

    monkeypatch.setattr(adapter, "fetch_json", fake_fetch_json)
    try:
        records = _collect(adapter.fetch("drug/event", search="term", limit=2))
    finally:
        _run(client.aclose())
    assert [record["id"] for record in records] == ["a", "b"]
    assert captured and captured[0]["api_key"] == "demo"


def test_dailymed_fetch_returns_xml(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = DailyMedAdapter(context, client)

    async def fake_fetch_text(url: str, *, params: Any | None = None, headers: Any | None = None) -> str:
        return "<document><setid root='123'/></document>"

    monkeypatch.setattr(adapter, "fetch_text", fake_fetch_text)
    try:
        records = _collect(adapter.fetch("abc"))
    finally:
        _run(client.aclose())
    assert records == ["<document><setid root='123'/></document>"]


def test_rxnorm_fetch_uses_identifier(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = RxNormAdapter(context, client)

    async def fake_fetch_json(url: str, *, params: Any | None = None, headers: Any | None = None) -> Any:
        return {"properties": {"rxcui": "12345"}}

    monkeypatch.setattr(adapter, "fetch_json", fake_fetch_json)
    try:
        records = _collect(adapter.fetch("12345"))
    finally:
        _run(client.aclose())
    assert records[0]["properties"]["rxcui"] == "12345"


def test_accessgudid_fetch_retrieves_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()
    adapter = AccessGudidAdapter(context, client)

    async def fake_fetch_json(url: str, *, params: Any | None = None, headers: Any | None = None) -> Any:
        return {"udi": {"deviceIdentifier": "01234567890123"}}

    monkeypatch.setattr(adapter, "fetch_json", fake_fetch_json)
    try:
        records = _collect(adapter.fetch("01234567890123"))
    finally:
        _run(client.aclose())
    assert records[0]["udi"]["deviceIdentifier"] == "01234567890123"


def test_guideline_fetch_variants(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()

    nice = NiceGuidelineAdapter(context, client)

    async def nice_json(*_args: Any, **_kwargs: Any) -> Any:
        return {"items": [{"uid": "NG1", "title": "Guideline"}]}

    monkeypatch.setattr(nice, "fetch_json", nice_json)
    assert _collect(nice.fetch())[0]["uid"] == "NG1"

    socrata = CdcSocrataAdapter(context, client)

    async def socrata_json(*_args: Any, **_kwargs: Any) -> Any:
        return [{"row_id": "row-1"}]

    monkeypatch.setattr(socrata, "fetch_json", socrata_json)
    assert _collect(socrata.fetch("dataset"))[0]["row_id"] == "row-1"

    who = WhoGhoAdapter(context, client)

    async def who_json(*_args: Any, **_kwargs: Any) -> Any:
        return {"value": [{"Indicator": "A", "Value": 1, "SpatialDim": "US", "TimeDim": "2024"}]}

    monkeypatch.setattr(who, "fetch_json", who_json)
    assert _collect(who.fetch("indicator"))[0]["Indicator"] == "A"

    openprescribing = OpenPrescribingAdapter(context, client)

    async def openprescribing_json(*_args: Any, **_kwargs: Any) -> Any:
        return [{"practice": "ABC"}]

    monkeypatch.setattr(openprescribing, "fetch_json", openprescribing_json)
    assert _collect(openprescribing.fetch("endpoint"))[0]["practice"] == "ABC"

    wonder = CdcWonderAdapter(context, client)
    with pytest.raises(RuntimeError):
        _collect(wonder.fetch())


def test_literature_fetch_generators(monkeypatch: pytest.MonkeyPatch) -> None:
    ledger = FakeLedger()
    context = make_adapter_context(ledger)
    client = AsyncHttpClient()

    pubmed = PubMedAdapter(context, client)
    json_responses = [
        {"esearchresult": {"idlist": ["123"], "count": "0"}},
        {"result": {"uids": ["123"], "123": {"uid": "123", "pmid": "123", "title": "Summary"}}},
    ]

    async def pubmed_fetch_json(url: str, *, params: Any | None = None, headers: Any | None = None) -> Any:
        return json_responses.pop(0)

    async def pubmed_fetch_text(url: str, *, params: Any | None = None, headers: Any | None = None) -> str:
        return (
            "<PubmedArticleSet><PubmedArticle><MedlineCitation><PMID>123</PMID><Article><ArticleTitle>Title</ArticleTitle>"
            "<Abstract><AbstractText>Abstract</AbstractText></Abstract>"
            "<Journal><Title>Journal</Title><JournalIssue><PubDate><Year>2024</Year></PubDate></JournalIssue></Journal>"
            "<AuthorList><Author><LastName>Doe</LastName><ForeName>Jane</ForeName></Author></AuthorList>"
            "<PublicationTypeList><PublicationType>Clinical Trial</PublicationType></PublicationTypeList>"
            "</Article><MeshHeadingList><MeshHeading><DescriptorName>Term</DescriptorName></MeshHeading></MeshHeadingList>"
            "</MedlineCitation><PubmedData><ArticleIdList><ArticleId IdType='pmc'>PMC123</ArticleId>"
            "<ArticleId IdType='doi'>10.123/example</ArticleId></ArticleIdList></PubmedData></PubmedArticle></PubmedArticleSet>"
        )

    monkeypatch.setattr(pubmed, "fetch_json", pubmed_fetch_json)
    monkeypatch.setattr(pubmed, "fetch_text", pubmed_fetch_text)
    pubmed_records = _collect(pubmed.fetch("cancer"))
    assert pubmed_records and pubmed_records[0]["pmid"] == "123"

    pmc = PmcAdapter(context, client)
    pmc_xml = [
        """
        <OAI-PMH>
          <ListRecords>
            <record><header><identifier>oai:pmc:PMC1</identifier><datestamp>2024-01-01</datestamp></header></record>
          </ListRecords>
          <resumptionToken>next</resumptionToken>
        </OAI-PMH>
        """,
        """
        <OAI-PMH>
          <ListRecords>
            <record><header><identifier>oai:pmc:PMC2</identifier><datestamp>2024-01-02</datestamp></header></record>
          </ListRecords>
        </OAI-PMH>
        """,
    ]

    async def pmc_fetch_text(url: str, *, params: Any | None = None, headers: Any | None = None) -> str:
        return pmc_xml.pop(0)

    monkeypatch.setattr(pmc, "fetch_text", pmc_fetch_text)
    pmc_records = _collect(pmc.fetch("set"))
    assert len(pmc_records) == 2

    medrxiv = MedRxivAdapter(context, client)
    medrxiv_payloads = [
        {"results": [{"doi": "10.1/abc", "title": "One"}], "next_cursor": "token"},
        {"results": [{"doi": "10.1/def", "title": "Two"}], "next_cursor": None},
    ]

    async def medrxiv_fetch_json(url: str, *, params: Any | None = None, headers: Any | None = None) -> Any:
        return medrxiv_payloads.pop(0)

    monkeypatch.setattr(medrxiv, "fetch_json", medrxiv_fetch_json)
    medrxiv_records = _collect(medrxiv.fetch(page_size=1))
    assert [record["doi"] for record in medrxiv_records] == ["10.1/abc", "10.1/def"]

