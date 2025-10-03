from __future__ import annotations

from Medical_KG.entity_linking.candidates import Candidate
from Medical_KG.entity_linking.decision import DecisionEngine, LinkingDecision
from Medical_KG.entity_linking.detectors import IdentifierCandidate
from Medical_KG.entity_linking.llm import AdjudicationResult


def _candidate(identifier: str, score: float) -> Candidate:
    return Candidate(identifier=identifier, ontology="rxnorm", score=score, label=identifier, metadata={})


def test_decision_accepts_high_confidence_llm() -> None:
    engine = DecisionEngine(acceptance_threshold=0.7)
    llm = AdjudicationResult(chosen_id="rx1", ontology="rxnorm", score=0.9, evidence_span={}, alternates=[], notes=None)
    decision = engine.decide(llm, [_candidate("rx1", 0.8)], [])

    assert decision == LinkingDecision(True, _candidate("rx1", 0.8))


def test_decision_falls_back_to_deterministic_identifier() -> None:
    engine = DecisionEngine(acceptance_threshold=0.9)
    llm = AdjudicationResult(chosen_id=None, ontology=None, score=0.0, evidence_span={}, alternates=[], notes=None)
    identifiers = [IdentifierCandidate(scheme="RxCUI", code="1234", confidence=0.95, start=0, end=4)]

    decision = engine.decide(llm, [], identifiers)

    assert decision.accepted is True
    assert decision.reason == "deterministic"
    assert decision.candidate and decision.candidate.identifier == "1234"


def test_decision_uses_highest_scoring_candidate() -> None:
    engine = DecisionEngine(acceptance_threshold=0.6)
    llm = AdjudicationResult(chosen_id=None, ontology=None, score=0.0, evidence_span={}, alternates=[], notes=None)
    candidates = [_candidate("rx1", 0.4), _candidate("rx2", 0.8)]

    decision = engine.decide(llm, candidates, [])

    assert decision.accepted is True
    assert decision.reason == "score-threshold"
    assert decision.candidate and decision.candidate.identifier == "rx2"


def test_decision_returns_low_confidence_when_no_support() -> None:
    engine = DecisionEngine(acceptance_threshold=0.9)
    llm = AdjudicationResult(chosen_id=None, ontology=None, score=0.0, evidence_span={}, alternates=[], notes=None)

    decision = engine.decide(llm, [], [])

    assert decision == LinkingDecision(False, None, reason="low-confidence")

