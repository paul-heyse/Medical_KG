"""Repository abstractions for briefing outputs."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Mapping, Protocol

from .models import (
    AdverseEvent,
    Dose,
    EligibilityConstraint,
    Evidence,
    EvidenceVariable,
    GuidelineRecommendation,
    Study,
    Topic,
    TopicBundle,
)


class BriefingRepository(Protocol):
    """Interface for fetching topic-aligned graph entities."""

    def load_topic_bundle(self, topic: Topic) -> TopicBundle:
        ...


@dataclass
class InMemoryBriefingRepository:
    """Simple repository backed by dictionaries. Useful for testing."""

    bundles: Dict[tuple[str, str, str], TopicBundle] = field(default_factory=dict)

    def register(self, bundle: TopicBundle) -> None:
        key = (bundle.topic.condition, bundle.topic.intervention, bundle.topic.outcome)
        self.bundles[key] = bundle

    def load_topic_bundle(self, topic: Topic) -> TopicBundle:
        key = (topic.condition, topic.intervention, topic.outcome)
        if key not in self.bundles:
            raise KeyError(f"Topic not found: {topic}")
        return self.bundles[key]


class DelegatedBriefingRepository:
    """Repository that proxies to another repository while applying read-only filters."""

    def __init__(self, backend: BriefingRepository, *, vocabulary_filters: Mapping[str, bool] | None = None) -> None:
        self._backend = backend
        self._filters = {k.lower(): bool(v) for k, v in (vocabulary_filters or {}).items()}

    def load_topic_bundle(self, topic: Topic) -> TopicBundle:
        bundle = self._backend.load_topic_bundle(topic)
        if not self._filters:
            return bundle
        if not self._filters.get("snomed", True):
            studies = _redact_vocab(bundle.studies, vocab="SNOMED")
        else:
            studies = bundle.studies
        if not self._filters.get("meddra", True):
            aes = _redact_vocab(bundle.adverse_events, vocab="MedDRA")
        else:
            aes = bundle.adverse_events
        return TopicBundle(
            topic=bundle.topic,
            studies=studies,
            evidence_variables=bundle.evidence_variables,
            evidence=bundle.evidence,
            adverse_events=aes,
            doses=bundle.doses,
            eligibility=bundle.eligibility,
            guidelines=bundle.guidelines,
        )


def _redact_vocab(items: Iterable[Study | AdverseEvent], *, vocab: str) -> list:
    redacted: list = []
    for item in items:
        if isinstance(item, Study):
            redacted.append(Study(item.study_id, title=f"[{vocab} redacted]", registry_ids=item.registry_ids, citations=item.citations))
        else:
            redacted.append(
                AdverseEvent(
                    study_id=item.study_id,
                    meddra_pt=f"[{vocab} redacted]",
                    grade=item.grade,
                    rate=item.rate,
                    numerator=item.numerator,
                    denominator=item.denominator,
                    citations=item.citations,
                )
            )
    return redacted


__all__ = [
    "BriefingRepository",
    "InMemoryBriefingRepository",
    "DelegatedBriefingRepository",
]
