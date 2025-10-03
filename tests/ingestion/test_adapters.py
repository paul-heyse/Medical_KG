from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any, Callable, Mapping, MutableMapping, cast

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
    CdcWonderAdapter,
    NiceGuidelineAdapter,
    OpenPrescribingAdapter,
    UspstfAdapter,
    WhoGhoAdapter,
)
from Medical_KG.ingestion.adapters.literature import (
    LiteratureFallback,
    LiteratureFallbackError,
    MedRxivAdapter,
    PmcAdapter,
    PubMedAdapter,
)
from Medical_KG.ingestion.adapters.terminology import (
    Icd11Adapter,
    LoincAdapter,
    MeSHAdapter,
    SnomedAdapter,
    UMLSAdapter,
)
from Medical_KG.ingestion.http_client import AsyncHttpClient
from Medical_KG.ingestion.models import Document
from Medical_KG.utils.optional_dependencies import get_httpx_module
from tests.ingestion.fixtures.clinical import (
    accessgudid_record,
    clinical_study,
    clinical_study_without_outcomes,
    dailymed_xml,
    openfda_faers_record,
    openfda_udi_record,
)
from tests.ingestion.fixtures.guidelines import (
    cdc_socrata_record,
    cdc_socrata_record_with_identifier,
    cdc_socrata_record_without_row_identifier,
    cdc_wonder_xml,
    cdc_wonder_xml_without_rows,
    nice_guideline,
    nice_guideline_with_optional_fields,
    nice_guideline_without_optional_fields,
    openprescribing_record_with_row_identifier,
    openprescribing_record_without_row_identifier,
    uspstf_record_with_optional_fields,
    uspstf_record_without_optional_fields,
    who_gho_record_with_optional_fields,
    who_gho_record_without_optional_fields,
)
from tests.ingestion.fixtures.literature import (
    medrxiv_record,
    medrxiv_record_without_date,
    pmc_record_xml,
    pubmed_document_with_optional_fields,
    pubmed_document_without_optional_fields,
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


def _run(coro: Any) -> Any:
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def _stub_http_client() -> AsyncHttpClient:
    class _Stub:
        def set_rate_limit(self, *_: object, **__: object) -> None:
            return None

    return cast(AsyncHttpClient, _Stub())


def test_pubmed_adapter_parses_fixture(fake_ledger: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _test() -> None:
        client = AsyncHttpClient()
        adapter = PubMedAdapter(AdapterContext(fake_ledger), client)

        search_payload = pubmed_search_payload()
        summary_payload = pubmed_summary_payload()
        fetch_payload = pubmed_fetch_xml()

        async def fake_fetch_json(url: str, **_: Any) -> dict[str, Any]:
            return search_payload if "esearch" in url else summary_payload

        async def fake_fetch_text(url: str, **_: Any) -> str:
            assert "efetch" in url
            return fetch_payload

        monkeypatch.setattr(adapter, "fetch_json", fake_fetch_json)
        monkeypatch.setattr(adapter, "fetch_text", fake_fetch_text)

        results = await adapter.run(term="sepsis", retmax=10)
        assert len(results) == 1
        document = results[0].document
        assert document.metadata["pmid"] == "12345678"
        assert isinstance(document.raw, dict)
        assert "mesh_terms" in document.raw
        await client.aclose()

    _run(_test())


def test_pubmed_adapter_handles_missing_history(
    fake_ledger: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _test() -> None:
        client = AsyncHttpClient()
        adapter = PubMedAdapter(AdapterContext(fake_ledger), client)

        search_payload = pubmed_search_without_history()
        summary_payload = pubmed_summary_payload()
        fetch_payload = pubmed_fetch_xml()

        async def fake_fetch_json(url: str, **_: Any) -> dict[str, Any]:
            return search_payload if "esearch" in url else summary_payload

        async def fake_fetch_text(url: str, **_: Any) -> str:
            return fetch_payload

        monkeypatch.setattr(adapter, "fetch_json", fake_fetch_json)
        monkeypatch.setattr(adapter, "fetch_text", fake_fetch_text)

        results = await adapter.run(term="oncology")
        assert results
        await client.aclose()

    _run(_test())


def test_pubmed_rate_limit_adjusts_for_api_key(fake_ledger: Any) -> None:
    client_without_key = AsyncHttpClient()
    adapter_without_key = PubMedAdapter(AdapterContext(fake_ledger), client_without_key)
    client_with_key = AsyncHttpClient()
    adapter_with_key = PubMedAdapter(AdapterContext(fake_ledger), client_with_key, api_key="token")
    host = "eutils.ncbi.nlm.nih.gov"
    assert adapter_without_key.client._limits[host].rate == 3
    assert adapter_with_key.client._limits[host].rate == 10
    _run(client_without_key.aclose())
    _run(client_with_key.aclose())


def test_pubmed_validate_rejects_non_pubmed_payload(fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    adapter = PubMedAdapter(AdapterContext(fake_ledger), client)
    document = Document(
        doc_id="doc-1",
        source="pubmed",
        content="",
        metadata={},
        raw={
            "code": "123456",
            "display": "Hypertension",
            "designation": [{"value": "Hypertension"}],
        },
    )
    with pytest.raises(ValueError):
        adapter.validate(document)
    _run(client.aclose())


def test_clinical_trials_parses_metadata(fake_ledger: Any) -> None:
    async def _test() -> None:
        client = AsyncHttpClient()
        adapter = ClinicalTrialsGovAdapter(
            AdapterContext(fake_ledger), client, bootstrap_records=[clinical_study()]
        )
        results = await adapter.run()
        document = results[0].document
        assert document.metadata["record_version"] == "2024-01-01"
        assert document.raw["phase"]
        assert isinstance(document.raw, dict)
        assert isinstance(document.raw["arms"], list)
        assert isinstance(document.raw.get("outcomes"), list)
        assert isinstance(document.raw["eligibility"], str)
        await client.aclose()

    _run(_test())


def test_clinical_trials_handles_partial_payload(fake_ledger: Any) -> None:
    async def _test() -> None:
        client = AsyncHttpClient()
        adapter = ClinicalTrialsGovAdapter(
            AdapterContext(fake_ledger),
            client,
            bootstrap_records=[clinical_study_without_outcomes()],
        )
        results = await adapter.run()
        payload = results[0].document.raw
        assert isinstance(payload, dict)
        assert payload.get("outcomes") is None
        assert isinstance(payload["arms"], list)
        await client.aclose()

    _run(_test())


def test_clinical_trials_validate_rejects_invalid(fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    adapter = ClinicalTrialsGovAdapter(AdapterContext(fake_ledger), client)
    document = adapter.parse(clinical_study())
    document.raw["nct_id"] = "BAD"
    with pytest.raises(ValueError):
        adapter.validate(document)
    _run(client.aclose())


def test_clinical_trials_paginates(fake_ledger: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _test() -> None:
        client = AsyncHttpClient()
        adapter = ClinicalTrialsGovAdapter(AdapterContext(fake_ledger), client)
        calls: list[MutableMapping[str, Any]] = []

        async def fake_fetch_json(
            url: str, *, params: MutableMapping[str, Any] | None = None, **_: Any
        ) -> dict[str, Any]:
            assert params is not None
            calls.append(dict(params))
            if "pageToken" in params:
                return {
                    "studies": [{"protocolSection": {"identificationModule": {"nctId": "NCT2"}}}]
                }
            return {
                "studies": [{"protocolSection": {"identificationModule": {"nctId": "NCT1"}}}],
                "nextPageToken": "token",
            }

        monkeypatch.setattr(adapter, "fetch_json", fake_fetch_json)
        collected: list[str] = []
        async for record in adapter.fetch():
            nct = record["protocolSection"]["identificationModule"]["nctId"]
            collected.append(nct)

        assert collected == ["NCT1", "NCT2"]
        assert len(calls) == 2
        await client.aclose()

    _run(_test())


@pytest.mark.parametrize("status", [404, 500])
def test_clinical_trials_propagates_http_errors(
    fake_ledger: Any, httpx_mock_transport: Any, status: int
) -> None:
    HTTPX = get_httpx_module()

    def handler(request: Any) -> Any:
        response = HTTPX.Response(status_code=status, request=request, text="error")
        return response

    httpx_mock_transport(handler)
    client = AsyncHttpClient()
    adapter = ClinicalTrialsGovAdapter(AdapterContext(fake_ledger), client)
    with pytest.raises(HTTPX.HTTPStatusError):
        _run(adapter.run())
    _run(client.aclose())


def test_clinical_trials_retries_on_rate_limit(
    fake_ledger: Any, httpx_mock_transport: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    HTTPX = get_httpx_module()
    calls: list[str] = []

    studies_payload = {"studies": [clinical_study()]}

    def handler(request: Any) -> Any:
        calls.append(str(request.url))
        if len(calls) == 1:
            return HTTPX.Response(
                status_code=429,
                headers={"Retry-After": "0"},
                request=request,
                text="rate limited",
            )
        return HTTPX.Response(status_code=200, json=studies_payload, request=request)

    httpx_mock_transport(handler)

    async def _sleep(_: float) -> None:
        return None

    monkeypatch.setattr("Medical_KG.ingestion.http_client.asyncio.sleep", _sleep)

    client = AsyncHttpClient()
    adapter = ClinicalTrialsGovAdapter(AdapterContext(fake_ledger), client)
    results = _run(adapter.run())
    assert len(results) == 1
    assert len(calls) == 2
    _run(client.aclose())


def test_clinical_trials_metadata_enrichment(fake_ledger: Any) -> None:
    record = clinical_study()
    protocol = record.setdefault("protocolSection", {})
    protocol.setdefault("sponsorCollaboratorsModule", {})["leadSponsor"] = {
        "name": "Example Sponsor"
    }
    protocol.setdefault("designModule", {}).setdefault("enrollmentInfo", {})["count"] = 256
    status_module = protocol.setdefault("statusModule", {})
    status_module["startDateStruct"] = {"date": "2024-05-01"}
    status_module["completionDateStruct"] = {"date": "2025-10-31"}

    client = AsyncHttpClient()
    adapter = ClinicalTrialsGovAdapter(
        AdapterContext(fake_ledger), client, bootstrap_records=[record]
    )
    results = _run(adapter.run())
    metadata = results[0].document.metadata
    assert metadata["sponsor"] == "Example Sponsor"
    assert metadata["enrollment"] == 256
    assert metadata["start_date"] == "2024-05-01"
    assert metadata["completion_date"] == "2025-10-31"
    _run(client.aclose())


def test_openfda_requires_identifier(fake_ledger: Any) -> None:
    async def _test() -> None:
        client = AsyncHttpClient()
        adapter = OpenFdaAdapter(
            AdapterContext(fake_ledger), client, bootstrap_records=[{"foo": "bar"}]
        )
        with pytest.raises(ValueError):
            await adapter.run(resource="drug/event")
        await client.aclose()

    _run(_test())


def test_openfda_parses_identifier(fake_ledger: Any) -> None:
    async def _test() -> None:
        client = AsyncHttpClient()
        adapter = OpenFdaAdapter(
            AdapterContext(fake_ledger), client, bootstrap_records=[openfda_faers_record()]
        )
        results = await adapter.run(resource="drug/event")
        assert results[0].document.metadata["identifier"]
        assert isinstance(results[0].document.raw["record"], dict)
        await client.aclose()

    _run(_test())


def test_openfda_udi_enriches_metadata(fake_ledger: Any) -> None:
    async def _test() -> None:
        client = AsyncHttpClient()
        adapter = OpenFdaUdiAdapter(
            AdapterContext(fake_ledger), client, bootstrap_records=[openfda_udi_record()]
        )
        results = await adapter.run(resource="device/udi")
        metadata = results[0].document.metadata
        assert metadata["identifier"]
        assert metadata["udi_di"].isdigit()
        assert isinstance(results[0].document.raw["record"], dict)
        await client.aclose()

    _run(_test())


def test_accessgudid_validation(fake_ledger: Any) -> None:
    async def _test() -> None:
        payload = accessgudid_record()
        client = AsyncHttpClient()
        adapter = AccessGudidAdapter(
            AdapterContext(fake_ledger), client, bootstrap_records=[payload]
        )
        results = await adapter.run(udi_di="00380740000011")
        assert results[0].document.metadata["udi_di"] == "00380740000011"
        await client.aclose()

    _run(_test())


def test_accessgudid_rejects_bad_udi(fake_ledger: Any) -> None:
    async def _test() -> None:
        payload = accessgudid_record()
        payload["udi"]["deviceIdentifier"] = "1234"
        client = AsyncHttpClient()
        adapter = AccessGudidAdapter(
            AdapterContext(fake_ledger), client, bootstrap_records=[payload]
        )
        with pytest.raises(ValueError):
            await adapter.run(udi_di="1234")
        await client.aclose()

    _run(_test())


def test_dailymed_parses_sections(fake_ledger: Any) -> None:
    async def _test() -> None:
        client = AsyncHttpClient()
        adapter = DailyMedAdapter(
            AdapterContext(fake_ledger), client, bootstrap_records=[dailymed_xml()]
        )
        results = await adapter.run(setid="setid")
        sections = results[0].document.raw["sections"]
        assert sections and sections[0]["text"]
        await client.aclose()

    _run(_test())


def test_pmc_adapter_collects_tables(fake_ledger: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _test() -> None:
        client = AsyncHttpClient()
        adapter = PmcAdapter(AdapterContext(fake_ledger), client)

        async def fake_fetch_text(*_: Any, **__: Any) -> str:
            return f"<OAI>{pmc_record_xml()}</OAI>"

        monkeypatch.setattr(adapter, "fetch_text", fake_fetch_text)
        results = await adapter.run(set_spec="pmc")
        document = results[0].document
        assert document.metadata["pmcid"] == "PMC1234567"
        assert document.metadata["datestamp"] == "2024-01-15"
        assert "Sepsis" in document.content
        assert isinstance(document.raw, dict)
        await client.aclose()

    _run(_test())


def test_pmc_adapter_extracts_sections_and_references(
    fake_ledger: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _test() -> None:
        client = AsyncHttpClient()
        adapter = PmcAdapter(AdapterContext(fake_ledger), client)
        xml_payload = """
        <record>
          <header>
            <identifier>oai:pubmedcentral.nih.gov:PMC999999</identifier>
            <datestamp>2024-02-02</datestamp>
          </header>
          <metadata>
            <article>
              <front>
                <article-title>Fallback Study</article-title>
              </front>
              <body>
                <sec>
                  <title>Introduction</title>
                  <p>Sepsis overview</p>
                </sec>
                <table-wrap>
                  <label>Table 1</label>
                  <caption><p>Data summary</p></caption>
                </table-wrap>
              </body>
              <back>
                <ref-list>
                  <ref>
                    <label>1</label>
                    <mixed-citation>Example reference</mixed-citation>
                  </ref>
                </ref-list>
              </back>
            </article>
          </metadata>
        </record>
        """

        async def fake_fetch_text(*_: object, **__: object) -> str:
            return f"<OAI>{xml_payload}</OAI>"

        monkeypatch.setattr(adapter, "fetch_text", fake_fetch_text)
        results = await adapter.run(set_spec="pmc")
        payload = results[0].document.raw
        assert isinstance(payload, dict)
        assert payload["sections"]
        assert payload["references"]
        assert payload["tables"]
        await client.aclose()

    _run(_test())


def test_medrxiv_paginates(fake_ledger: Any, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _test() -> None:
        client = AsyncHttpClient()
        adapter = MedRxivAdapter(AdapterContext(fake_ledger), client)

        async def fake_fetch_json(*_: Any, **__: Any) -> dict[str, Any]:
            if not getattr(fake_fetch_json, "called", False):
                fake_fetch_json.called = True  # type: ignore[attr-defined]
                return {"results": [medrxiv_record()], "next_cursor": "next"}
            return {"results": [medrxiv_record()], "next_cursor": None}

        fake_fetch_json.called = False  # type: ignore[attr-defined]
        monkeypatch.setattr(adapter, "fetch_json", fake_fetch_json)

        results = await adapter.run()
        assert len(results) == 2
        await client.aclose()

    _run(_test())


def test_guideline_adapters(fake_ledger: Any) -> None:
    async def _test() -> None:
        client = AsyncHttpClient()
        nice = NiceGuidelineAdapter(
            AdapterContext(fake_ledger), client, bootstrap_records=[nice_guideline()]
        )
        cdc = CdcSocrataAdapter(
            AdapterContext(fake_ledger), client, bootstrap_records=cdc_socrata_record()
        )
        nic_results = await nice.run()
        cdc_results = await cdc.run(dataset="abc")
        assert nic_results[0].document.metadata["uid"].startswith("CG")
        assert isinstance(nic_results[0].document.raw, dict)
        assert isinstance(nic_results[0].document.raw["summary"], str)
        assert nic_results[0].document.raw["url"] is None or isinstance(
            nic_results[0].document.raw["url"], str
        )
        assert cdc_results[0].document.metadata["identifier"].startswith("CA-")
        assert isinstance(cdc_results[0].document.raw["record"], dict)
        await client.aclose()

    _run(_test())


def test_terminology_adapters_parse(fake_ledger: Any) -> None:
    async def _test() -> None:
        client = AsyncHttpClient()
        context = AdapterContext(fake_ledger)
        mesh = MeSHAdapter(context, client, bootstrap_records=[mesh_descriptor()])
        umls = UMLSAdapter(context, client, bootstrap_records=[umls_record()])
        loinc = LoincAdapter(context, client, bootstrap_records=[loinc_record()])
        icd = Icd11Adapter(context, client, bootstrap_records=[icd11_record()])
        snomed = SnomedAdapter(context, client, bootstrap_records=[snomed_record()])
        rxnorm = RxNormAdapter(context, client, bootstrap_records=[rxnav_properties()])

        results = await asyncio.gather(
            mesh.run(descriptor_id="D012345"),
            umls.run(cui="C1234567"),
            loinc.run(code="4548-4"),
            icd.run(code="1A00"),
            snomed.run(code="44054006"),
            rxnorm.run(rxcui="12345"),
        )

        assert results[0][0].document.metadata["descriptor_id"].startswith("D")
        assert isinstance(results[0][0].document.raw, dict)
        assert results[1][0].document.metadata["cui"].startswith("C")
        assert isinstance(results[1][0].document.raw, dict)
        assert results[2][0].document.metadata["code"].endswith("-4")
        assert isinstance(results[2][0].document.raw, dict)
        assert results[5][0].document.metadata["rxcui"].isdigit()
        assert isinstance(results[3][0].document.raw["title"], str)
        assert isinstance(results[4][0].document.raw["designation"], list)
        await client.aclose()

    _run(_test())


def test_terminology_validations(fake_ledger: Any) -> None:
    client = AsyncHttpClient()
    context = AdapterContext(fake_ledger)
    document = Document("doc", "mesh", "")

    mesh = MeSHAdapter(context, client, bootstrap_records=[mesh_descriptor()])
    document.metadata = {"descriptor_id": "BAD"}
    with pytest.raises(ValueError):
        mesh.validate(document)

    umls = UMLSAdapter(context, client, bootstrap_records=[umls_record()])
    document.metadata = {"cui": "BAD"}
    with pytest.raises(ValueError):
        umls.validate(document)

    loinc = LoincAdapter(context, client, bootstrap_records=[loinc_record()])
    document.metadata = {"code": "BAD"}
    with pytest.raises(ValueError):
        loinc.validate(document)

    icd = Icd11Adapter(context, client, bootstrap_records=[icd11_record()])
    with pytest.raises(ValueError):
        icd.validate(Document("doc", "icd", "", metadata={"code": "X"}, raw={}))

    snomed = SnomedAdapter(context, client, bootstrap_records=[snomed_record()])
    with pytest.raises(ValueError):
        snomed.validate(
            Document("doc", "snomed", "", metadata={"code": "12"}, raw={"designation": []})
        )

    _run(client.aclose())


def test_literature_optional_field_variants(fake_ledger: Any) -> None:
    context = AdapterContext(fake_ledger)
    stub_client = _stub_http_client()

    pubmed = PubMedAdapter(context, stub_client)
    optional_pubmed = pubmed.parse(pubmed_document_with_optional_fields())
    assert isinstance(optional_pubmed.raw, dict)
    assert optional_pubmed.raw.get("pmcid") == "PMC1234567"
    assert optional_pubmed.raw.get("doi") == "10.1000/example.doi"
    minimal_pubmed = pubmed.parse(pubmed_document_without_optional_fields())
    assert isinstance(minimal_pubmed.raw, dict)
    assert minimal_pubmed.raw.get("pmcid") is None
    assert minimal_pubmed.raw.get("doi") is None

    medrxiv = MedRxivAdapter(context, stub_client)
    medrxiv_missing = medrxiv.parse(medrxiv_record_without_date())
    assert isinstance(medrxiv_missing.raw, dict)
    assert medrxiv_missing.raw.get("date") is None
    medrxiv_present = medrxiv.parse(medrxiv_record())
    assert isinstance(medrxiv_present.raw, dict)
    assert medrxiv_present.raw.get("date") is not None


@pytest.mark.parametrize(
    (
        "adapter_factory",
        "present_payload",
        "absent_payload",
        "raw_optional_keys",
        "metadata_optional_keys",
        "allow_absent_validation_error",
    ),
    (
        (
            lambda context, client: NiceGuidelineAdapter(context, client),
            nice_guideline_with_optional_fields,
            nice_guideline_without_optional_fields,
            ("url", "licence"),
            ("licence",),
            False,
        ),
        (
            lambda context, client: UspstfAdapter(context, client),
            uspstf_record_with_optional_fields,
            uspstf_record_without_optional_fields,
            ("id", "status", "url"),
            ("id", "status"),
            True,
        ),
    ),
    ids=("nice", "uspstf"),
)
def test_guideline_optional_field_variants(
    fake_ledger: Any,
    adapter_factory: Callable[[AdapterContext, AsyncHttpClient], BaseAdapter[Any]],
    present_payload: Callable[[], Any],
    absent_payload: Callable[[], Any],
    raw_optional_keys: tuple[str, ...],
    metadata_optional_keys: tuple[str, ...],
    allow_absent_validation_error: bool,
) -> None:
    context = AdapterContext(fake_ledger)
    adapter = adapter_factory(context, _stub_http_client())
    present_document = adapter.parse(present_payload())
    absent_document = adapter.parse(absent_payload())
    assert isinstance(present_document.raw, dict)
    assert isinstance(absent_document.raw, dict)
    for key in raw_optional_keys:
        assert key in present_document.raw
        assert present_document.raw[key] not in (None, "", [], {})
        if key in absent_document.raw:
            assert absent_document.raw[key] in (None, "", [], {})
    for key in metadata_optional_keys:
        assert key in present_document.metadata
        assert key not in absent_document.metadata
    adapter.validate(present_document)
    if allow_absent_validation_error:
        with pytest.raises(ValueError):
            adapter.validate(absent_document)
    else:
        adapter.validate(absent_document)


@pytest.mark.parametrize(
    (
        "adapter_factory",
        "present_payload",
        "absent_payload",
        "raw_optional_keys",
        "allow_absent_validation_error",
    ),
    (
        (
            lambda context, client: CdcSocrataAdapter(context, client),
            cdc_socrata_record_with_identifier,
            cdc_socrata_record_without_row_identifier,
            (),
            False,
        ),
        (
            lambda context, client: CdcWonderAdapter(context, client),
            cdc_wonder_xml,
            cdc_wonder_xml_without_rows,
            (),
            True,
        ),
        (
            lambda context, client: WhoGhoAdapter(context, client),
            who_gho_record_with_optional_fields,
            who_gho_record_without_optional_fields,
            ("indicator", "country", "year"),
            False,
        ),
        (
            lambda context, client: OpenPrescribingAdapter(context, client),
            openprescribing_record_with_row_identifier,
            openprescribing_record_without_row_identifier,
            (),
            False,
        ),
    ),
    ids=("cdc_socrata", "cdc_wonder", "who_gho", "openprescribing"),
)
def test_knowledge_base_optional_field_variants(
    fake_ledger: Any,
    adapter_factory: Callable[[AdapterContext, AsyncHttpClient], BaseAdapter[Any]],
    present_payload: Callable[[], Any],
    absent_payload: Callable[[], Any],
    raw_optional_keys: tuple[str, ...],
    allow_absent_validation_error: bool,
) -> None:
    context = AdapterContext(fake_ledger)
    adapter = adapter_factory(context, _stub_http_client())
    present_document = adapter.parse(present_payload())
    absent_document = adapter.parse(absent_payload())
    assert isinstance(present_document.raw, dict)
    assert isinstance(absent_document.raw, dict)
    for key in raw_optional_keys:
        assert key in present_document.raw
        assert present_document.raw[key] not in (None, "", [], {})
        if key in absent_document.raw:
            assert absent_document.raw[key] in (None, "", [], {})
    adapter.validate(present_document)
    if allow_absent_validation_error:
        with pytest.raises(ValueError):
            adapter.validate(absent_document)
    else:
        adapter.validate(absent_document)


def test_literature_fallback_returns_first_success() -> None:
    document = Document(doc_id="doc-1", source="pubmed", content="text")

    class _FakeAdapter:
        def __init__(self, source: str, results: list[Document], *, raises: bool = False) -> None:
            self.source = source
            self._results = results
            self._raises = raises
            self.calls = 0

        async def run(self, **_: Any) -> list[SimpleNamespace]:
            self.calls += 1
            if self._raises:
                raise RuntimeError("adapter failure")
            return [SimpleNamespace(document=doc) for doc in self._results]

    first = _FakeAdapter("pmc", [], raises=False)
    second = _FakeAdapter("pubmed", [document], raises=False)
    third = _FakeAdapter("medrxiv", [document], raises=False)
    fallback = LiteratureFallback(first, second, third)
    docs, source = _run(fallback.run())
    assert source == "pubmed"
    assert docs == [document]
    assert first.calls == 1 and second.calls == 1 and third.calls == 0


def test_literature_fallback_raises_when_all_fail() -> None:
    class _Failing:
        source = "pmc"

        async def run(self, **_: Any) -> list[SimpleNamespace]:
            raise RuntimeError("boom")

    fallback = LiteratureFallback(_Failing(), _Failing())
    with pytest.raises(LiteratureFallbackError):
        _run(fallback.run())


def test_terminology_adapters_cache_responses(
    fake_ledger: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _test() -> None:
        client = AsyncHttpClient()
        adapter = MeSHAdapter(AdapterContext(fake_ledger), client)
        calls = 0

        async def fake_fetch_json(*_: Any, **__: Any) -> dict[str, Any]:
            nonlocal calls
            calls += 1
            return mesh_descriptor()

        monkeypatch.setattr(adapter, "fetch_json", fake_fetch_json)
        await adapter.run(descriptor_id="D012345")
        await adapter.run(descriptor_id="D012345")
        assert calls == 1
        await client.aclose()

    _run(_test())


def test_udi_validator() -> None:
    assert UdiValidator.validate("00380740000011") is True
    assert UdiValidator.validate("12345678901234") is False


class _FailingAdapter(BaseAdapter):
    source = "fail"

    async def fetch(self, *_: Any, **__: Any) -> AsyncIterator[Mapping[str, Any]]:
        yield {"id": "1"}

    def parse(self, raw: Mapping[str, Any]) -> Document:
        return Document("doc-1", self.source, "", raw=raw, metadata={})

    def validate(self, document: Document) -> None:
        raise RuntimeError("boom")


class _SuccessfulAdapter(BaseAdapter):
    source = "success"

    async def fetch(self, *_: Any, **__: Any) -> AsyncIterator[Mapping[str, Any]]:
        yield {"id": "7"}

    def parse(self, raw: Mapping[str, Any]) -> Document:
        return Document("doc-7", self.source, "payload", metadata={"source": self.source}, raw=raw)

    def validate(self, document: Document) -> None:  # noqa: D401
        assert document.metadata["source"] == self.source


def test_base_adapter_records_failures(fake_ledger: Any) -> None:
    adapter = _FailingAdapter(AdapterContext(fake_ledger))
    with pytest.raises(RuntimeError):
        _run(adapter.run())
    entry = fake_ledger.get("doc-1")
    assert entry is not None
    assert entry.state == "auto_failed"
    assert "boom" in entry.metadata.get("error", "")


def test_base_adapter_records_success(fake_ledger: Any) -> None:
    adapter = _SuccessfulAdapter(AdapterContext(fake_ledger))
    results = _run(adapter.run())
    assert results[0].document.doc_id == "doc-7"
    entry = fake_ledger.get("doc-7")
    assert entry is not None and entry.state == "auto_done"
