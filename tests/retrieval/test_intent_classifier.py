import re

import pytest

from Medical_KG.retrieval.intent import IntentClassifier, IntentRule


@pytest.fixture
def intent_rules() -> list[IntentRule]:
    return [
        IntentRule(
            name="entity_lookup",
            keywords=(re.compile(r"pembrolizumab", re.I), re.compile(r"nct\d+", re.I)),
            boosts={"title_path": 3.0},
            filters={"facet": ["drug"]},
        ),
        IntentRule(
            name="pathway",
            keywords=(re.compile(r"egfr"), re.compile(r"signaling")),
            boosts={"body": 1.4},
            filters={"entity_type": "pathway"},
        ),
        IntentRule(
            name="general",
            keywords=(re.compile(r".*"),),
            boosts={},
            filters={},
        ),
    ]


def test_entity_lookup_detection(intent_rules: list[IntentRule]) -> None:
    classifier = IntentClassifier(intent_rules)
    detected = classifier.detect("What is pembrolizumab?")
    assert detected == "entity_lookup"
    boosts, filters = classifier.context_for(detected)
    assert boosts["title_path"] == pytest.approx(3.0)
    assert filters["facet"] == ["drug"]


def test_pathway_detection(intent_rules: list[IntentRule]) -> None:
    classifier = IntentClassifier(intent_rules)
    detected = classifier.detect("How does EGFR signaling work?")
    assert detected == "pathway"
    _, filters = classifier.context_for(detected)
    assert filters == {"entity_type": "pathway"}


def test_open_ended_default(intent_rules: list[IntentRule]) -> None:
    classifier = IntentClassifier(intent_rules)
    detected = classifier.detect("What are the latest cancer treatments?")
    assert detected == "general"


def test_ambiguous_intent_falls_back(intent_rules: list[IntentRule]) -> None:
    classifier = IntentClassifier(intent_rules)
    detected = classifier.detect("Explain treatment options")
    assert detected == "general"
    boosts, filters = classifier.context_for("unknown")
    assert boosts == {}
    assert filters == {}
