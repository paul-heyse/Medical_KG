"""Briefing output generation utilities."""

from Medical_KG.utils.optional_dependencies import (
    MissingDependencyError,
    optional_import,
)

try:  # pragma: no cover - optional FastAPI dependency for router wiring
    _api_module = optional_import(
        "Medical_KG.briefing.api",
        feature_name="fastapi",
        package_name="fastapi",
    )
except MissingDependencyError:  # pragma: no cover - fallback when fastapi/pydantic absent
    router = None  # type: ignore[assignment]
else:
    router = getattr(_api_module, "router", None)
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
