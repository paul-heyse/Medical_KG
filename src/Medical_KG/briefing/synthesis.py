"""Synthesis utilities for briefing outputs."""
from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean
from typing import Iterable, Mapping, MutableMapping

from .models import AdverseEvent, Citation, Dose, EligibilityConstraint, Evidence, EvidenceVariable, TopicBundle


def build_pico(bundle: TopicBundle) -> Mapping[str, list[Mapping[str, object]]]:
    sections: MutableMapping[str, list[Mapping[str, object]]] = defaultdict(list)
    for variable in bundle.evidence_variables:
        sections[variable.kind].append(
            {
                "description": variable.description,
                "citations": [citation.as_dict() for citation in variable.citations],
            }
        )
    return sections


def build_endpoint_summary(bundle: TopicBundle) -> list[Mapping[str, object]]:
    grouped: MutableMapping[tuple[str, str], list[Evidence]] = defaultdict(list)
    for evidence in bundle.evidence:
        grouped[(evidence.outcome, evidence.intervention)].append(evidence)

    summaries: list[Mapping[str, object]] = []
    for (outcome, intervention), evidences in grouped.items():
        summary = {
            "outcome": outcome,
            "intervention": intervention,
            "certainty": _highest_certainty(evidences),
            "meta": _meta_analysis(evidences),
            "citations": [citation.as_dict() for citation in _collect_citations(evidences)],
        }
        summaries.append(summary)
    return sorted(summaries, key=lambda item: (item["outcome"], item["intervention"]))


def _highest_certainty(evidences: Iterable[Evidence]) -> str:
    ordering = {"very high": 4, "high": 3, "moderate": 2, "low": 1, "very low": 0}
    highest = max(evidences, key=lambda ev: ordering.get(ev.certainty.lower(), 0))
    return highest.certainty


def _meta_analysis(evidences: list[Evidence]) -> Mapping[str, object]:
    values = [ev.value for ev in evidences]
    ci_values = [ev for ev in evidences if ev.has_interval()]
    if len(ci_values) >= 2:
        pooled, ci_low, ci_high, i2 = _random_effects(ci_values)
        return {
            "type": ci_values[0].effect_type,
            "pooled": pooled,
            "ci_low": ci_low,
            "ci_high": ci_high,
            "i2": i2,
            "studies": [ev.study_id for ev in evidences],
        }
    return {
        "type": evidences[0].effect_type,
        "values": values,
        "studies": [ev.study_id for ev in evidences],
        "i2": None,
    }


def _random_effects(evidences: list[Evidence]) -> tuple[float, float, float, float]:
    weights: list[float] = []
    effects: list[float] = []
    for ev in evidences:
        assert ev.ci_low is not None and ev.ci_high is not None
        se = (ev.ci_high - ev.ci_low) / (2 * 1.96)
        weight = 1 / (se**2)
        weights.append(weight)
        effects.append(ev.value)
    fixed_effect = sum(w * e for w, e in zip(weights, effects)) / sum(weights)
    q = sum(w * (e - fixed_effect) ** 2 for w, e in zip(weights, effects))
    df = len(evidences) - 1
    tau_squared = max(0.0, (q - df) / max(sum(weights) - sum(w**2 for w in weights) / sum(weights), 1e-9))
    random_weights = [1 / (1 / w + tau_squared) for w in weights]
    pooled = sum(w * e for w, e in zip(random_weights, effects)) / sum(random_weights)
    se_pooled = math.sqrt(1 / sum(random_weights))
    ci_low = pooled - 1.96 * se_pooled
    ci_high = pooled + 1.96 * se_pooled
    i2 = max(0.0, min(100.0, ((q - df) / q) * 100 if q > df else 0.0))
    return pooled, ci_low, ci_high, i2


def _collect_citations(evidences: Iterable[Evidence]) -> list[Citation]:
    citations: list[Citation] = []
    for evidence in evidences:
        citations.extend(evidence.citations)
    return citations


def build_safety_profile(bundle: TopicBundle) -> list[Mapping[str, object]]:
    grouped: MutableMapping[tuple[str, int | None], list[AdverseEvent]] = defaultdict(list)
    for ae in bundle.adverse_events:
        grouped[(ae.meddra_pt, ae.grade)].append(ae)
    profile: list[Mapping[str, object]] = []
    for (term, grade), events in grouped.items():
        profile.append(
            {
                "term": term,
                "grade": grade,
                "rate": mean([ev.rate for ev in events if ev.rate is not None]) if events else None,
                "citations": [citation.as_dict() for citation in _collect_citations(events)],
            }
        )
    return sorted(profile, key=lambda item: (item["term"], item.get("grade") or 0))


def _collect_citations(events: Iterable[AdverseEvent | Dose | EligibilityConstraint]) -> list[Citation]:
    citations: list[Citation] = []
    for event in events:
        citations.extend(event.citations)
    return citations


def build_dosing(bundle: TopicBundle) -> list[Mapping[str, object]]:
    regimens: list[Mapping[str, object]] = []
    for dose in bundle.doses:
        regimens.append(
            {
                "description": dose.description,
                "amount": dose.amount,
                "unit": dose.unit,
                "frequency": dose.frequency,
                "citations": [citation.as_dict() for citation in dose.citations],
            }
        )
    return regimens


def build_eligibility(bundle: TopicBundle) -> list[Mapping[str, object]]:
    summary: list[Mapping[str, object]] = []
    for constraint in bundle.eligibility:
        summary.append(
            {
                "type": constraint.constraint_type,
                "description": constraint.description,
                "citations": [citation.as_dict() for citation in constraint.citations],
            }
        )
    return summary


def build_guideline_summary(bundle: TopicBundle) -> list[Mapping[str, object]]:
    entries: list[Mapping[str, object]] = []
    for guideline in bundle.guidelines:
        entries.append(
            {
                "guideline_id": guideline.guideline_id,
                "statement": guideline.statement,
                "strength": guideline.strength,
                "certainty": guideline.certainty,
                "citations": [citation.as_dict() for citation in guideline.citations],
            }
        )
    return entries


def detect_conflicts(bundle: TopicBundle) -> list[Mapping[str, object]]:
    conflicts: list[Mapping[str, object]] = []
    evidence_by_key: MutableMapping[tuple[str, str], list[Evidence]] = defaultdict(list)
    for ev in bundle.evidence:
        evidence_by_key[(ev.outcome, ev.intervention)].append(ev)
    for (outcome, intervention), evidences in evidence_by_key.items():
        positives = [ev for ev in evidences if ev.value > 1]
        negatives = [ev for ev in evidences if ev.value < 1]
        if positives and negatives:
            conflicts.append(
                {
                    "outcome": outcome,
                    "intervention": intervention,
                    "details": [
                        {
                            "study_id": ev.study_id,
                            "effect": ev.value,
                            "citations": [citation.as_dict() for citation in ev.citations],
                        }
                        for ev in evidences
                    ],
                }
            )
    return conflicts


def detect_gaps(bundle: TopicBundle) -> list[str]:
    mentioned_outcomes = {var.description for var in bundle.evidence_variables if var.kind == "outcome"}
    evidenced_outcomes = {ev.outcome for ev in bundle.evidence}
    return sorted(mentioned_outcomes - evidenced_outcomes)


__all__ = [
    "build_pico",
    "build_endpoint_summary",
    "build_safety_profile",
    "build_dosing",
    "build_eligibility",
    "build_guideline_summary",
    "detect_conflicts",
    "detect_gaps",
]
