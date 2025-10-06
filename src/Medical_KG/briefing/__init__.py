"""Briefing output generation utilities."""

from typing import Any

from Medical_KG.utils.optional_dependencies import (
    MissingDependencyError,
    optional_import,
)

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

router: Any | None

try:  # pragma: no cover - optional FastAPI dependency for router wiring
    _api_module = optional_import(
        "Medical_KG.briefing.api",
        feature_name="fastapi",
        package_name="fastapi",
    )
except MissingDependencyError:  # pragma: no cover - fallback when fastapi/pydantic absent
    router = None
else:
    router = getattr(_api_module, "router", None)

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
