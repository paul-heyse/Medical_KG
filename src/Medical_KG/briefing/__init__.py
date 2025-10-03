"""Briefing output generation utilities."""

try:  # pragma: no cover - optional FastAPI dependency for router wiring
    from .api import router
except ModuleNotFoundError:  # pragma: no cover - fallback when fastapi/pydantic absent
    router = None  # type: ignore[assignment]
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
