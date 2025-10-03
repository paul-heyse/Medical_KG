"""Briefing output generation utilities."""

from .api import router
from .models import (
    AdverseEvent,
    Citation,
    Dose,
    EligibilityConstraint,
    Evidence,
    EvidenceVariable,
    GuidelineRecommendation,
    Study,
    Topic,
    TopicBundle,
)
from .repository import InMemoryBriefingRepository
from .service import BriefingService, BriefingSettings

__all__ = [
    "router",
    "BriefingService",
    "BriefingSettings",
    "InMemoryBriefingRepository",
    "Citation",
    "EvidenceVariable",
    "Evidence",
    "AdverseEvent",
    "Dose",
    "EligibilityConstraint",
    "GuidelineRecommendation",
    "Study",
    "Topic",
    "TopicBundle",
    "InMemoryBriefingRepository",
]
