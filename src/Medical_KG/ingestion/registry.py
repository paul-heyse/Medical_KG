"""Adapter registry for ingestion CLI and orchestration."""

from __future__ import annotations

from typing import Callable, Dict, Type

from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.adapters.clinical import (
    AccessGudidAdapter,
    ClinicalTrialsGovAdapter,
    DailyMedAdapter,
    OpenFdaAdapter,
    OpenFdaUdiAdapter,
    RxNormAdapter,
)
from Medical_KG.ingestion.adapters.guidelines import (
    CdcSocrataAdapter,
    CdcWonderAdapter,
    NiceGuidelineAdapter,
    OpenPrescribingAdapter,
    UspstfAdapter,
    WhoGhoAdapter,
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

AdapterFactory = Callable[[AdapterContext, AsyncHttpClient], BaseAdapter]


def _register() -> Dict[str, AdapterFactory]:
    def factory(cls: Type[BaseAdapter]) -> AdapterFactory:
        def _builder(context: AdapterContext, client: AsyncHttpClient, **kwargs: object) -> BaseAdapter:
            return cls(context, client, **kwargs)

        return _builder

    return {
        "pubmed": factory(PubMedAdapter),
        "pmc": factory(PmcAdapter),
        "medrxiv": factory(MedRxivAdapter),
        "clinicaltrials": factory(ClinicalTrialsGovAdapter),
        "openfda": factory(OpenFdaAdapter),
        "dailymed": factory(DailyMedAdapter),
        "rxnorm": factory(RxNormAdapter),
        "mesh": factory(MeSHAdapter),
        "umls": factory(UMLSAdapter),
        "loinc": factory(LoincAdapter),
        "icd11": factory(Icd11Adapter),
        "snomed": factory(SnomedAdapter),
        "nice": factory(NiceGuidelineAdapter),
        "uspstf": factory(UspstfAdapter),
        "cdc_socrata": factory(CdcSocrataAdapter),
        "cdc_wonder": factory(CdcWonderAdapter),
        "who_gho": factory(WhoGhoAdapter),
        "openprescribing": factory(OpenPrescribingAdapter),
        "accessgudid": factory(AccessGudidAdapter),
        "openfda_udi": factory(OpenFdaUdiAdapter),
    }


_REGISTRY = _register()


def get_adapter(source: str, context: AdapterContext, client: AsyncHttpClient, **kwargs: Any) -> BaseAdapter:
    try:
        factory = _REGISTRY[source]
    except KeyError as exc:  # pragma: no cover - defensive
        raise ValueError(f"Unknown adapter source: {source}") from exc
    return factory(context, client, **kwargs)


def available_sources() -> list[str]:
    return sorted(_REGISTRY)
