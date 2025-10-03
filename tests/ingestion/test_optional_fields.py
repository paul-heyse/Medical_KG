"""Optional field regression coverage for ingestion adapters.

These tests exercise adapters with fixtures where every ``NotRequired`` field in
our TypedDict payloads is either populated or deliberately omitted. The goal is
threefold:

* ensure the adapter produces valid :class:`~Medical_KG.ingestion.models.Document`
  instances even when optional upstream data is missing,
* confirm optional metadata entries are only emitted when source values exist,
  and
* guard against regressions where optional keys unexpectedly disappear from
  payloads with complete data.

Future adapters should follow the same pattern: add fixtures representing both
"all optional fields present" and "all optional fields absent", then extend the
scenario tables below so each variant is validated during test execution.
"""

from __future__ import annotations

import importlib.util
import types
import typing
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import pytest

from Medical_KG.ingestion.adapters.base import AdapterContext, BaseAdapter
from Medical_KG.ingestion.adapters.clinical import (
    AccessGudidAdapter,
    ClinicalTrialsGovAdapter,
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
from Medical_KG.ingestion.adapters.literature import MedRxivAdapter, PubMedAdapter
from Medical_KG.ingestion.adapters.terminology import (
    Icd11Adapter,
    LoincAdapter,
    MeSHAdapter,
    SnomedAdapter,
    UMLSAdapter,
)
from Medical_KG.ingestion.models import Document
from tests.ingestion.fixtures.clinical import (
    accessgudid_record,
    accessgudid_record_without_optional_fields,
    clinical_study_with_optional_fields,
    clinical_study_without_optional_fields,
)
from tests.ingestion.fixtures.guidelines import (
    cdc_socrata_record_with_identifier,
    cdc_socrata_record_without_row_identifier,
    cdc_wonder_xml,
    cdc_wonder_xml_without_rows,
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
    pubmed_document_with_optional_fields,
    pubmed_document_without_optional_fields,
)
from tests.ingestion.fixtures.terminology import (
    icd11_record,
    icd11_record_without_optional_fields,
    loinc_record,
    loinc_record_without_optional_fields,
    mesh_descriptor,
    mesh_descriptor_without_descriptor_id,
    rxnav_properties,
    rxnav_properties_without_optional_fields,
    snomed_record,
    snomed_record_without_optional_fields,
    umls_record,
    umls_record_without_optional_fields,
)

AdapterFactory = Callable[[AdapterContext, Any], BaseAdapter[Any]]


@dataclass(slots=True)
class OptionalFieldScenario:
    name: str
    adapter_factory: AdapterFactory
    present_payload: Callable[[], Any]
    absent_payload: Callable[[], Any]
    raw_optional_keys: tuple[str, ...]
    metadata_optional_keys: tuple[str, ...] = ()
    metadata_requires_absence: bool = False
    expect_same_content: bool = True
    allow_absent_validation_error: bool = False
    raw_absent_values: dict[str, tuple[Any, ...]] | None = None


class _StubHttpClient:
    """Minimal stub satisfying adapter constructor requirements."""

    def set_rate_limit(self, *_args: object, **_kwargs: object) -> None:
        return None


def _parse_documents(
    adapter: BaseAdapter[Any],
    *,
    present_payload: Callable[[], Any],
    absent_payload: Callable[[], Any],
) -> tuple[Document, Document]:
    present_document = adapter.parse(present_payload())
    absent_document = adapter.parse(absent_payload())
    assert isinstance(present_document.raw, dict)
    assert isinstance(absent_document.raw, dict)
    assert isinstance(present_document.content, str)
    assert isinstance(absent_document.content, str)
    return present_document, absent_document


def _assert_optional_behaviour(
    scenario: OptionalFieldScenario,
    *,
    present_document: Document,
    absent_document: Document,
) -> None:
    for key in scenario.raw_optional_keys:
        assert key in present_document.raw
        assert present_document.raw[key] is not None
        if key in absent_document.raw:
            allowed_values = (
                scenario.raw_absent_values.get(key)
                if scenario.raw_absent_values is not None and key in scenario.raw_absent_values
                else (None, "", [], {})
            )
            assert absent_document.raw[key] in allowed_values
    for key in scenario.metadata_optional_keys:
        assert key in present_document.metadata
        if scenario.metadata_requires_absence:
            assert key not in absent_document.metadata
        else:
            if key in absent_document.metadata:
                assert absent_document.metadata[key] in (None, "", [], {})
    if scenario.expect_same_content:
        assert present_document.content == absent_document.content


def _validate_documents(
    adapter: BaseAdapter[Any],
    scenario: OptionalFieldScenario,
    *,
    present_document: Document,
    absent_document: Document,
) -> None:
    adapter.validate(present_document)
    if scenario.allow_absent_validation_error:
        with pytest.raises(ValueError):
            adapter.validate(absent_document)
    else:
        adapter.validate(absent_document)


TERMINOLOGY_SCENARIOS: tuple[OptionalFieldScenario, ...] = (
    OptionalFieldScenario(
        name="mesh",
        adapter_factory=lambda context, client: MeSHAdapter(context, client),
        present_payload=mesh_descriptor,
        absent_payload=mesh_descriptor_without_descriptor_id,
        raw_optional_keys=("descriptor_id",),
        expect_same_content=False,
        allow_absent_validation_error=True,
    ),
    OptionalFieldScenario(
        name="umls",
        adapter_factory=lambda context, client: UMLSAdapter(context, client),
        present_payload=umls_record,
        absent_payload=umls_record_without_optional_fields,
        raw_optional_keys=("cui", "name", "definition"),
        expect_same_content=False,
        allow_absent_validation_error=True,
    ),
    OptionalFieldScenario(
        name="loinc",
        adapter_factory=lambda context, client: LoincAdapter(context, client),
        present_payload=loinc_record,
        absent_payload=loinc_record_without_optional_fields,
        raw_optional_keys=("code", "display"),
        expect_same_content=False,
        raw_absent_values={"code": ("unknown",), "display": (None, "", [], {})},
        allow_absent_validation_error=True,
    ),
    OptionalFieldScenario(
        name="icd11",
        adapter_factory=lambda context, client: Icd11Adapter(context, client),
        present_payload=icd11_record,
        absent_payload=icd11_record_without_optional_fields,
        raw_optional_keys=("code", "title", "definition", "uri"),
        expect_same_content=False,
        allow_absent_validation_error=True,
    ),
    OptionalFieldScenario(
        name="snomed",
        adapter_factory=lambda context, client: SnomedAdapter(context, client),
        present_payload=snomed_record,
        absent_payload=snomed_record_without_optional_fields,
        raw_optional_keys=("code", "display"),
        expect_same_content=False,
        raw_absent_values={"code": ("unknown",), "display": (None, "", [], {})},
        allow_absent_validation_error=True,
    ),
)


CLINICAL_SCENARIOS: tuple[OptionalFieldScenario, ...] = (
    OptionalFieldScenario(
        name="clinicaltrials",
        adapter_factory=lambda context, client: ClinicalTrialsGovAdapter(context, client),
        present_payload=clinical_study_with_optional_fields,
        absent_payload=clinical_study_without_optional_fields,
        raw_optional_keys=(
            "status",
            "phase",
            "study_type",
            "lead_sponsor",
            "enrollment",
            "start_date",
            "completion_date",
            "outcomes",
        ),
        metadata_optional_keys=(
            "status",
            "sponsor",
            "phase",
            "enrollment",
            "start_date",
            "completion_date",
        ),
        metadata_requires_absence=True,
    ),
    OptionalFieldScenario(
        name="accessgudid",
        adapter_factory=lambda context, client: AccessGudidAdapter(context, client),
        present_payload=accessgudid_record,
        absent_payload=accessgudid_record_without_optional_fields,
        raw_optional_keys=("brand", "model", "company", "description"),
    ),
    OptionalFieldScenario(
        name="rxnorm",
        adapter_factory=lambda context, client: RxNormAdapter(context, client),
        present_payload=rxnav_properties,
        absent_payload=rxnav_properties_without_optional_fields,
        raw_optional_keys=("name", "synonym", "tty", "ndc"),
        expect_same_content=False,
    ),
)


LITERATURE_SCENARIOS: tuple[OptionalFieldScenario, ...] = (
    OptionalFieldScenario(
        name="pubmed",
        adapter_factory=lambda context, client: PubMedAdapter(context, client),
        present_payload=pubmed_document_with_optional_fields,
        absent_payload=pubmed_document_without_optional_fields,
        raw_optional_keys=("pmcid", "doi", "journal", "pub_year", "pubdate"),
        expect_same_content=False,
    ),
    OptionalFieldScenario(
        name="medrxiv",
        adapter_factory=lambda context, client: MedRxivAdapter(context, client),
        present_payload=medrxiv_record,
        absent_payload=medrxiv_record_without_date,
        raw_optional_keys=("date",),
        expect_same_content=False,
    ),
)


GUIDELINE_SCENARIOS: tuple[OptionalFieldScenario, ...] = (
    OptionalFieldScenario(
        name="nice",
        adapter_factory=lambda context, client: NiceGuidelineAdapter(context, client),
        present_payload=nice_guideline_with_optional_fields,
        absent_payload=nice_guideline_without_optional_fields,
        raw_optional_keys=("url", "licence"),
        metadata_optional_keys=("licence",),
        metadata_requires_absence=True,
        expect_same_content=False,
        allow_absent_validation_error=False,
    ),
    OptionalFieldScenario(
        name="uspstf",
        adapter_factory=lambda context, client: UspstfAdapter(context, client),
        present_payload=uspstf_record_with_optional_fields,
        absent_payload=uspstf_record_without_optional_fields,
        raw_optional_keys=("id", "status", "url"),
        metadata_optional_keys=("id", "status"),
        metadata_requires_absence=True,
        expect_same_content=False,
        allow_absent_validation_error=True,
    ),
)


KNOWLEDGE_BASE_SCENARIOS: tuple[OptionalFieldScenario, ...] = (
    OptionalFieldScenario(
        name="cdc_socrata",
        adapter_factory=lambda context, client: CdcSocrataAdapter(context, client),
        present_payload=cdc_socrata_record_with_identifier,
        absent_payload=cdc_socrata_record_without_row_identifier,
        raw_optional_keys=(),
        expect_same_content=False,
    ),
    OptionalFieldScenario(
        name="cdc_wonder",
        adapter_factory=lambda context, client: CdcWonderAdapter(context, client),
        present_payload=cdc_wonder_xml,
        absent_payload=cdc_wonder_xml_without_rows,
        raw_optional_keys=(),
        expect_same_content=False,
        allow_absent_validation_error=True,
    ),
    OptionalFieldScenario(
        name="who_gho",
        adapter_factory=lambda context, client: WhoGhoAdapter(context, client),
        present_payload=who_gho_record_with_optional_fields,
        absent_payload=who_gho_record_without_optional_fields,
        raw_optional_keys=("indicator", "country", "year"),
        expect_same_content=False,
    ),
    OptionalFieldScenario(
        name="openprescribing",
        adapter_factory=lambda context, client: OpenPrescribingAdapter(context, client),
        present_payload=openprescribing_record_with_row_identifier,
        absent_payload=openprescribing_record_without_row_identifier,
        raw_optional_keys=(),
        expect_same_content=False,
    ),
)


@pytest.mark.parametrize("scenario", TERMINOLOGY_SCENARIOS, ids=lambda s: s.name)
def test_terminology_optional_fields(fake_ledger: Any, scenario: OptionalFieldScenario) -> None:
    context = AdapterContext(fake_ledger)
    adapter = scenario.adapter_factory(context, _StubHttpClient())
    present_document, absent_document = _parse_documents(
        adapter,
        present_payload=scenario.present_payload,
        absent_payload=scenario.absent_payload,
    )
    _assert_optional_behaviour(
        scenario,
        present_document=present_document,
        absent_document=absent_document,
    )
    _validate_documents(
        adapter,
        scenario,
        present_document=present_document,
        absent_document=absent_document,
    )


@pytest.mark.parametrize("scenario", GUIDELINE_SCENARIOS, ids=lambda s: s.name)
def test_guideline_optional_fields(fake_ledger: Any, scenario: OptionalFieldScenario) -> None:
    context = AdapterContext(fake_ledger)
    adapter = scenario.adapter_factory(context, _StubHttpClient())
    present_document, absent_document = _parse_documents(
        adapter,
        present_payload=scenario.present_payload,
        absent_payload=scenario.absent_payload,
    )
    _assert_optional_behaviour(
        scenario,
        present_document=present_document,
        absent_document=absent_document,
    )
    _validate_documents(
        adapter,
        scenario,
        present_document=present_document,
        absent_document=absent_document,
    )


@pytest.mark.parametrize("scenario", KNOWLEDGE_BASE_SCENARIOS, ids=lambda s: s.name)
def test_knowledge_base_optional_fields(fake_ledger: Any, scenario: OptionalFieldScenario) -> None:
    context = AdapterContext(fake_ledger)
    adapter = scenario.adapter_factory(context, _StubHttpClient())
    present_document, absent_document = _parse_documents(
        adapter,
        present_payload=scenario.present_payload,
        absent_payload=scenario.absent_payload,
    )
    _assert_optional_behaviour(
        scenario,
        present_document=present_document,
        absent_document=absent_document,
    )
    _validate_documents(
        adapter,
        scenario,
        present_document=present_document,
        absent_document=absent_document,
    )


def _load_types_module() -> types.ModuleType:
    types_path = Path(__file__).resolve().parents[2] / "src" / "Medical_KG" / "ingestion" / "types.py"
    spec = importlib.util.spec_from_file_location("ingestion_types", types_path)
    if spec is None or spec.loader is None:  # pragma: no cover - defensive
        raise RuntimeError("Failed to load ingestion types module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_INGESTION_TYPES = _load_types_module()


def _collect_not_required_fields(typed_dict_cls: type[Any]) -> set[str]:
    hints = typing.get_type_hints(typed_dict_cls, globalns=_INGESTION_TYPES.__dict__, include_extras=True)
    optional_fields: set[str] = set()
    for field, annotation in hints.items():
        if typing.get_origin(annotation) is typing.NotRequired:
            optional_fields.add(field)
    return optional_fields


SCENARIO_TYPE_MAP: dict[str, type[Any]] = {
    "mesh": _INGESTION_TYPES.MeshDocumentPayload,
    "umls": _INGESTION_TYPES.UmlsDocumentPayload,
    "loinc": _INGESTION_TYPES.LoincDocumentPayload,
    "icd11": _INGESTION_TYPES.Icd11DocumentPayload,
    "snomed": _INGESTION_TYPES.SnomedDocumentPayload,
    "clinicaltrials": _INGESTION_TYPES.ClinicalDocumentPayload,
    "accessgudid": _INGESTION_TYPES.AccessGudidDocumentPayload,
    "rxnorm": _INGESTION_TYPES.RxNormDocumentPayload,
    "pubmed": _INGESTION_TYPES.PubMedDocumentPayload,
    "medrxiv": _INGESTION_TYPES.MedRxivDocumentPayload,
    "nice": _INGESTION_TYPES.NiceGuidelineDocumentPayload,
    "uspstf": _INGESTION_TYPES.UspstfDocumentPayload,
    "who_gho": _INGESTION_TYPES.WhoGhoDocumentPayload,
}


def test_not_required_fields_have_present_and_absent_scenarios() -> None:
    coverage: dict[str, set[str]] = {}
    for scenario in (
        TERMINOLOGY_SCENARIOS
        + CLINICAL_SCENARIOS
        + LITERATURE_SCENARIOS
        + GUIDELINE_SCENARIOS
        + KNOWLEDGE_BASE_SCENARIOS
    ):
        coverage.setdefault(scenario.name, set()).update(scenario.raw_optional_keys)
    for scenario_name, typed_dict_cls in SCENARIO_TYPE_MAP.items():
        optional_fields = _collect_not_required_fields(typed_dict_cls)
        if not optional_fields:
            continue
        missing = optional_fields - coverage.get(scenario_name, set())
        assert not missing, f"Missing optional field coverage for {scenario_name}: {sorted(missing)}"

@pytest.mark.parametrize("scenario", CLINICAL_SCENARIOS, ids=lambda s: s.name)
def test_clinical_optional_fields(fake_ledger: Any, scenario: OptionalFieldScenario) -> None:
    context = AdapterContext(fake_ledger)
    adapter = scenario.adapter_factory(context, _StubHttpClient())
    present_document, absent_document = _parse_documents(
        adapter,
        present_payload=scenario.present_payload,
        absent_payload=scenario.absent_payload,
    )
    _assert_optional_behaviour(
        scenario,
        present_document=present_document,
        absent_document=absent_document,
    )
    _validate_documents(
        adapter,
        scenario,
        present_document=present_document,
        absent_document=absent_document,
    )


@pytest.mark.parametrize("scenario", LITERATURE_SCENARIOS, ids=lambda s: s.name)
def test_literature_optional_fields(fake_ledger: Any, scenario: OptionalFieldScenario) -> None:
    context = AdapterContext(fake_ledger)
    adapter = scenario.adapter_factory(context, _StubHttpClient())
    present_document, absent_document = _parse_documents(
        adapter,
        present_payload=scenario.present_payload,
        absent_payload=scenario.absent_payload,
    )
    _assert_optional_behaviour(
        scenario,
        present_document=present_document,
        absent_document=absent_document,
    )
    _validate_documents(
        adapter,
        scenario,
        present_document=present_document,
        absent_document=absent_document,
    )
