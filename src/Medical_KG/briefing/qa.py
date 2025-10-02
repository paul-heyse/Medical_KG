"""Real-time Q&A heuristics for briefing outputs."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

from .models import Citation, Evidence, TopicBundle


@dataclass(frozen=True, slots=True)
class QAResult:
    answer: str
    intent: str
    evidence: Sequence[Mapping[str, object]]
    conflicts: Sequence[Mapping[str, object]]
    gaps: Sequence[str]


class IntentRouter:
    """Maps free-text queries to intents based on keywords."""

    def route(self, query: str) -> str:
        normalized = query.lower()
        if any(keyword in normalized for keyword in ("adverse", "safety", "ae")):
            return "ae"
        if any(keyword in normalized for keyword in ("dose", "dosing", "regimen")):
            return "dose"
        if any(keyword in normalized for keyword in ("eligibility", "inclusion", "exclusion")):
            return "eligibility"
        return "endpoint"


class QAEngine:
    """Synthesizes answers from a topic bundle."""

    def __init__(self, router: IntentRouter | None = None) -> None:
        self._router = router or IntentRouter()

    def answer(self, query: str, bundle: TopicBundle) -> QAResult:
        intent = self._router.route(query)
        if intent == "endpoint":
            evidences = bundle.evidence
            answer = self._summarize_effect(evidences)
            evidence_payload = [self._format_evidence(ev) for ev in evidences]
        elif intent == "ae":
            answer = self._summarize_items(bundle.adverse_events, field="meddra_pt")
            evidence_payload = [self._format_generic(ae.meddra_pt, ae.citations) for ae in bundle.adverse_events]
        elif intent == "dose":
            answer = self._summarize_items(bundle.doses, field="description")
            evidence_payload = [self._format_generic(dose.description, dose.citations) for dose in bundle.doses]
        else:
            answer = self._summarize_items(bundle.eligibility, field="description")
            evidence_payload = [self._format_generic(item.description, item.citations) for item in bundle.eligibility]
        conflicts: list[Mapping[str, object]] = []
        if intent == "endpoint":
            conflicts = [self._format_conflict(group) for group in _find_conflicting_effects(bundle.evidence)]
        gaps = _find_gaps(bundle, intent)
        return QAResult(answer=answer, intent=intent, evidence=evidence_payload, conflicts=conflicts, gaps=gaps)

    def _summarize_effect(self, evidences: Sequence[Evidence]) -> str:
        if not evidences:
            return "No evidence found."
        best = max(evidences, key=lambda ev: ev.certainty)
        return (
            f"{best.intervention} shows {best.effect_type}={best.value:.2f} for {best.outcome}"
            f" ({best.certainty} certainty)."
        )

    def _summarize_items(self, items: Sequence[object], *, field: str) -> str:
        if not items:
            return "No data available."
        values = {getattr(item, field) for item in items}
        return "; ".join(sorted(str(value) for value in values))

    def _format_evidence(self, evidence: Evidence) -> Mapping[str, object]:
        return {
            "study_id": evidence.study_id,
            "effect": evidence.value,
            "certainty": evidence.certainty,
            "citations": [citation.as_dict() for citation in evidence.citations],
        }

    def _format_generic(self, text: str, citations: Sequence[Citation]) -> Mapping[str, object]:
        return {
            "text": text,
            "citations": [citation.as_dict() for citation in citations],
        }

    def _format_conflict(self, evidences: Sequence[Evidence]) -> Mapping[str, object]:
        return {
            "outcome": evidences[0].outcome,
            "intervention": evidences[0].intervention,
            "studies": [self._format_evidence(ev) for ev in evidences],
        }


def _find_conflicting_effects(evidences: Iterable[Evidence]) -> list[list[Evidence]]:
    conflicts: list[list[Evidence]] = []
    groups: dict[tuple[str, str], list[Evidence]] = {}
    for evidence in evidences:
        groups.setdefault((evidence.outcome, evidence.intervention), []).append(evidence)
    for group in groups.values():
        positives = [ev for ev in group if ev.value > 1]
        negatives = [ev for ev in group if ev.value < 1]
        if positives and negatives:
            conflicts.append(group)
    return conflicts


def _find_gaps(bundle: TopicBundle, intent: str) -> list[str]:
    if intent == "endpoint":
        mentioned = {var.description for var in bundle.evidence_variables if var.kind == "outcome"}
        observed = {ev.outcome for ev in bundle.evidence}
        return sorted(mentioned - observed)
    if intent == "ae":
        return [] if bundle.adverse_events else ["No adverse events reported"]
    if intent == "dose":
        return [] if bundle.doses else ["No dosing data"]
    return [] if bundle.eligibility else ["No eligibility data"]


__all__ = ["QAEngine", "QAResult", "IntentRouter"]
