from __future__ import annotations

import math

import pytest

from Medical_KG.briefing import synthesis
from Medical_KG.briefing.models import (
    AdverseEvent,
    Citation,
    Dose,
    EligibilityConstraint,
    Evidence,
    EvidenceVariable,
    GuidelineRecommendation,
    Topic,
    TopicBundle,
)


@pytest.fixture
def sample_bundle() -> TopicBundle:
    citation_a = Citation(doc_id="doc-a", start=0, end=10, quote="sample quote")
    citation_b = Citation(doc_id="doc-b", start=5, end=15, quote="another")
    evidence_variables = (
        EvidenceVariable(kind="population", description="Adults", citations=(citation_a,)),
        EvidenceVariable(kind="outcome", description="Overall survival", citations=(citation_b,)),
        EvidenceVariable(kind="outcome", description="Relapse-free survival", citations=(citation_a,)),
    )
    evidence = (
        Evidence(
            study_id="s1",
            population="Adults",
            intervention="Drug X",
            outcome="Overall survival",
            effect_type="risk_ratio",
            value=1.2,
            ci_low=1.0,
            ci_high=1.4,
            p_value=0.03,
            certainty="High",
            citations=(citation_a,),
        ),
        Evidence(
            study_id="s2",
            population="Adults",
            intervention="Drug X",
            outcome="Overall survival",
            effect_type="risk_ratio",
            value=0.8,
            ci_low=0.6,
            ci_high=1.0,
            p_value=0.20,
            certainty="Moderate",
            citations=(citation_b,),
        ),
        Evidence(
            study_id="s3",
            population="Adults",
            intervention="Drug Y",
            outcome="Progression-free survival",
            effect_type="odds_ratio",
            value=1.6,
            ci_low=None,
            ci_high=None,
            p_value=0.05,
            certainty="Low",
            citations=(citation_a,),
        ),
    )
    adverse_events = (
        AdverseEvent(
            study_id="s1",
            meddra_pt="Nausea",
            grade=2,
            rate=0.2,
            numerator=2,
            denominator=10,
            citations=(citation_a,),
        ),
        AdverseEvent(
            study_id="s2",
            meddra_pt="Nausea",
            grade=2,
            rate=0.4,
            numerator=4,
            denominator=10,
            citations=(citation_b,),
        ),
        AdverseEvent(
            study_id="s2",
            meddra_pt="Fatigue",
            grade=None,
            rate=0.1,
            numerator=None,
            denominator=None,
            citations=(citation_b,),
        ),
    )
    doses = (
        Dose(
            study_id="s1",
            description="50mg twice daily",
            amount=50.0,
            unit="mg",
            frequency="BID",
            citations=(citation_a,),
        ),
    )
    eligibility = (
        EligibilityConstraint(
            constraint_type="inclusion",
            description="Age between 18 and 70",
            citations=(citation_a,),
        ),
    )
    guidelines = (
        GuidelineRecommendation(
            guideline_id="g1",
            statement="Recommended for first-line therapy",
            strength="Strong",
            certainty="High",
            citations=(citation_b,),
        ),
    )
    return TopicBundle(
        topic=Topic(condition="Cancer", intervention="Drug X", outcome="Survival"),
        studies=(),
        evidence_variables=evidence_variables,
        evidence=evidence,
        adverse_events=adverse_events,
        doses=doses,
        eligibility=eligibility,
        guidelines=guidelines,
    )


def test_build_pico_groups_variables(sample_bundle: TopicBundle) -> None:
    pico = synthesis.build_pico(sample_bundle)

    assert sorted(pico.keys()) == ["outcome", "population"]
    assert pico["population"][0]["description"] == "Adults"
    assert pico["population"][0]["citations"][0]["doc_id"] == "doc-a"


def test_build_endpoint_summary_handles_meta_and_values(sample_bundle: TopicBundle) -> None:
    summary = synthesis.build_endpoint_summary(sample_bundle)

    assert len(summary) == 2

    first = summary[0]
    assert first["outcome"] == "Overall survival"
    meta = first["meta"]
    assert meta["type"] == "risk_ratio"
    assert meta["studies"] == ["s1", "s2"]
    assert meta["pooled"] == pytest.approx(1.0, rel=0.1)
    assert meta["ci_low"] < meta["pooled"] < meta["ci_high"]
    assert 0.0 <= meta["i2"] <= 100.0

    second = summary[1]
    assert second["meta"]["values"] == [1.6]
    assert second["meta"]["i2"] is None


def test_build_safety_profile_averages_rates(sample_bundle: TopicBundle) -> None:
    profile = synthesis.build_safety_profile(sample_bundle)
    nausea_entry = next(item for item in profile if item["term"] == "Nausea")

    assert math.isclose(nausea_entry["rate"], 0.3, rel_tol=1e-9)
    assert len(nausea_entry["citations"]) == 2


def test_build_other_sections(sample_bundle: TopicBundle) -> None:
    assert synthesis.build_dosing(sample_bundle)[0]["description"] == "50mg twice daily"
    assert synthesis.build_eligibility(sample_bundle)[0]["type"] == "inclusion"
    assert synthesis.build_guideline_summary(sample_bundle)[0]["guideline_id"] == "g1"


def test_detect_conflicts_and_gaps(sample_bundle: TopicBundle) -> None:
    conflicts = synthesis.detect_conflicts(sample_bundle)
    assert conflicts[0]["outcome"] == "Overall survival"
    assert {detail["effect"] for detail in conflicts[0]["details"]} == {0.8, 1.2}

    gaps = synthesis.detect_gaps(sample_bundle)
    assert gaps == ["Relapse-free survival"]
