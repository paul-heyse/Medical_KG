from __future__ import annotations

import json

import pytest

# ruff: noqa: E402
fastapi = pytest.importorskip("fastapi")
TestClient = pytest.importorskip("fastapi.testclient").TestClient

from Medical_KG.app import create_app
from Medical_KG.briefing import (
    AdverseEvent,
    BriefingService,
    Citation,
    Dose,
    EligibilityConstraint,
    Evidence,
    EvidenceVariable,
    GuidelineRecommendation,
    InMemoryBriefingRepository,
    Study,
    Topic,
    TopicBundle,
)
from Medical_KG.briefing.api import _get_dependencies


@pytest.fixture()
def topic_bundle() -> TopicBundle:
    topic = Topic(condition="SNOMED:123", intervention="RxCUI:456", outcome="LOINC:789")
    citation = Citation(doc_id="PMID:1", start=0, end=10, quote="Example quote")
    studies = [Study(study_id="NCT0001", title="Trial 1", registry_ids=["NCT0001"], citations=[citation])]
    variables = [
        EvidenceVariable(kind="population", description="Adults with condition", citations=[citation]),
        EvidenceVariable(kind="outcome", description="LOINC:789", citations=[citation]),
    ]
    evidence = [
        Evidence(
            study_id="NCT0001",
            population="Adults",
            intervention="RxCUI:456",
            outcome="LOINC:789",
            effect_type="HR",
            value=0.8,
            ci_low=0.6,
            ci_high=0.95,
            p_value=0.04,
            certainty="High",
            citations=[citation],
        ),
        Evidence(
            study_id="NCT0002",
            population="Adults",
            intervention="RxCUI:456",
            outcome="LOINC:789",
            effect_type="HR",
            value=1.3,
            ci_low=1.1,
            ci_high=1.6,
            p_value=0.02,
            certainty="Moderate",
            citations=[citation],
        ),
    ]
    aes = [
        AdverseEvent(
            study_id="NCT0001",
            meddra_pt="Nausea",
            grade=2,
            rate=0.12,
            numerator=12,
            denominator=100,
            citations=[citation],
        )
    ]
    doses = [
        Dose(
            study_id="NCT0001",
            description="50 mg twice daily",
            amount=50,
            unit="mg",
            frequency="BID",
            citations=[citation],
        )
    ]
    eligibility = [
        EligibilityConstraint(constraint_type="inclusion", description="Age 18-65", citations=[citation])
    ]
    guidelines = [
        GuidelineRecommendation(
            guideline_id="GUIDE1",
            statement="Use RxCUI:456 for SNOMED:123",
            strength="Strong",
            certainty="Moderate",
            citations=[citation],
        )
    ]
    return TopicBundle(
        topic=topic,
        studies=studies,
        evidence_variables=variables,
        evidence=evidence,
        adverse_events=aes,
        doses=doses,
        eligibility=eligibility,
        guidelines=guidelines,
    )


@pytest.fixture()
def repository(topic_bundle: TopicBundle) -> InMemoryBriefingRepository:
    repo = InMemoryBriefingRepository()
    repo.register(topic_bundle)
    return repo


def test_dossier_generates_all_sections(repository: InMemoryBriefingRepository, topic_bundle: TopicBundle) -> None:
    service = BriefingService(repository)
    dossier = service.dossier(topic_bundle.topic, format="json")
    payload = json.loads(dossier["content"])
    assert {section["title"] for section in payload["sections"]} == {
        "PICO",
        "Endpoints",
        "Safety",
        "Dosing",
        "Eligibility",
        "Guidelines",
    }
    assert dossier["bibliography"][0]["doc_id"] == "PMID:1"


def test_evidence_map_highlights_conflicts(repository: InMemoryBriefingRepository, topic_bundle: TopicBundle) -> None:
    service = BriefingService(repository)
    evidence_map = service.evidence_map(topic_bundle.topic)
    assert evidence_map["conflicts"], "Expected conflict when effects disagree"
    assert evidence_map["gaps"], "Outcome variable without evidence should be reported as gap"


def test_qa_endpoint_via_fastapi(repository: InMemoryBriefingRepository, topic_bundle: TopicBundle) -> None:
    app = create_app()
    app.dependency_overrides[_get_dependencies] = lambda: type("Deps", (), {"repository": repository})()
    client = TestClient(app)
    response = client.post(
        "/briefing/qa",
        json={
            "topic": {
                "condition": topic_bundle.topic.condition,
                "intervention": topic_bundle.topic.intervention,
                "outcome": topic_bundle.topic.outcome,
            },
            "query": "Does the intervention help the outcome?",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["intent"] == "endpoint"
    assert body["evidence"], "Should return supporting evidence"

