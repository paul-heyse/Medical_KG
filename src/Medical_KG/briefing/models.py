"""Domain models supporting briefing output synthesis."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence


@dataclass(frozen=True, slots=True)
class Citation:
    """Reference to an evidence span within a document."""

    doc_id: str
    start: int
    end: int
    quote: str

    def as_dict(self) -> Mapping[str, object]:
        return {
            "doc_id": self.doc_id,
            "start": self.start,
            "end": self.end,
            "quote": self.quote,
        }


@dataclass(frozen=True, slots=True)
class EvidenceVariable:
    """PICO variable captured in the KG."""

    kind: str
    description: str
    citations: Sequence[Citation] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Study:
    """Study level metadata used for coverage reporting."""

    study_id: str
    title: str
    registry_ids: Sequence[str] = field(default_factory=tuple)
    citations: Sequence[Citation] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class Evidence:
    """Quantitative outcome evidence."""

    study_id: str
    population: str
    intervention: str
    outcome: str
    effect_type: str
    value: float
    ci_low: float | None
    ci_high: float | None
    p_value: float | None
    certainty: str
    citations: Sequence[Citation]

    def has_interval(self) -> bool:
        return self.ci_low is not None and self.ci_high is not None and self.ci_low < self.ci_high


@dataclass(frozen=True, slots=True)
class AdverseEvent:
    """Safety signal extracted from the KG."""

    study_id: str
    meddra_pt: str
    grade: int | None
    rate: float | None
    numerator: int | None
    denominator: int | None
    citations: Sequence[Citation]


@dataclass(frozen=True, slots=True)
class Dose:
    """Dose guidance extracted from interventions."""

    study_id: str
    description: str
    amount: float | None
    unit: str | None
    frequency: str | None
    citations: Sequence[Citation]


@dataclass(frozen=True, slots=True)
class EligibilityConstraint:
    """Eligibility inclusion or exclusion criteria."""

    constraint_type: str
    description: str
    citations: Sequence[Citation]


@dataclass(frozen=True, slots=True)
class GuidelineRecommendation:
    """Guideline stance for the topic."""

    guideline_id: str
    statement: str
    strength: str
    certainty: str
    citations: Sequence[Citation]


@dataclass(frozen=True, slots=True)
class Topic:
    """Topic descriptor used to query the KG."""

    condition: str
    intervention: str
    outcome: str


@dataclass(frozen=True, slots=True)
class TopicBundle:
    """Collection of KG entities related to a topic."""

    topic: Topic
    studies: Sequence[Study]
    evidence_variables: Sequence[EvidenceVariable]
    evidence: Sequence[Evidence]
    adverse_events: Sequence[AdverseEvent]
    doses: Sequence[Dose]
    eligibility: Sequence[EligibilityConstraint]
    guidelines: Sequence[GuidelineRecommendation]

    def all_citations(self) -> Iterable[Citation]:
        for iterable in (
            self.studies,
            self.evidence_variables,
            self.evidence,
            self.adverse_events,
            self.doses,
            self.eligibility,
            self.guidelines,
        ):
            for item in iterable:
                yield from getattr(item, "citations", [])

