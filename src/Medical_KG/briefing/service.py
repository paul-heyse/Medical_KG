"""Service orchestrating briefing output generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .citation import CitationManager
from .formatters import BriefingFormatter
from .models import Topic, TopicBundle
from .qa import QAEngine, QAResult
from .repository import BriefingRepository
from .synthesis import (
    build_dosing,
    build_eligibility,
    build_endpoint_summary,
    build_guideline_summary,
    build_pico,
    build_safety_profile,
    detect_conflicts,
    detect_gaps,
)


@dataclass(slots=True)
class BriefingSettings:
    """Runtime settings for briefing outputs."""

    format_default: str = "json"
    citation_documents: Mapping[str, int] | None = None


class BriefingService:
    """Coordinates dossier creation, evidence maps, interview kits, and Q&A."""

    def __init__(
        self,
        repository: BriefingRepository,
        *,
        formatter: BriefingFormatter | None = None,
        qa_engine: QAEngine | None = None,
        settings: BriefingSettings | None = None,
    ) -> None:
        self._repository = repository
        self._formatter = formatter or BriefingFormatter()
        self._qa_engine = qa_engine or QAEngine()
        self._settings = settings or BriefingSettings()
        self._citations = CitationManager(self._settings.citation_documents)

    def dossier(self, topic: Topic, *, format: str | None = None) -> dict[str, object]:
        bundle = self._repository.load_topic_bundle(topic)
        payload = self._build_payload(bundle)
        rendered = self._render(payload, format or self._settings.format_default)
        citations = self._citations.aggregate(bundle.all_citations())
        bibliography = self._citations.bibliography(bundle.all_citations())
        return {
            "format": format or self._settings.format_default,
            "content": rendered,
            "citations": citations,
            "bibliography": bibliography,
        }

    def evidence_map(self, topic: Topic) -> dict[str, object]:
        bundle = self._repository.load_topic_bundle(topic)
        conflicts = detect_conflicts(bundle)
        gaps = detect_gaps(bundle)
        entries = build_endpoint_summary(bundle)
        return {
            "map": entries,
            "conflicts": conflicts,
            "gaps": gaps,
        }

    def interview_kit(self, topic: Topic) -> dict[str, object]:
        bundle = self._repository.load_topic_bundle(topic)
        gaps = detect_gaps(bundle)
        conflicts = detect_conflicts(bundle)
        questions: list[dict[str, object]] = [
            {
                "question": f"What is known about {gap}?",
                "priority": 1,
                "citations": [],
            }
            for gap in gaps
        ]
        for conflict in conflicts:
            details = conflict.get("details")
            citations = []
            if isinstance(details, list) and details:
                first = details[0]
                if isinstance(first, dict):
                    citations_value = first.get("citations", [])
                    if isinstance(citations_value, list):
                        citations = citations_value
            questions.append(
                {
                    "question": f"Why do studies disagree on {conflict['outcome']}?",
                    "priority": 2,
                    "citations": citations,
                }
            )
        questions.sort(key=_priority_sort_key)
        return {
            "questions": questions,
            "context": {
                "gaps": gaps,
                "conflicts": conflicts,
            },
        }

    def coverage(self, topic: Topic) -> dict[str, object]:
        bundle = self._repository.load_topic_bundle(topic)
        studies = [
            {
                "study_id": study.study_id,
                "title": study.title,
                "registry_ids": list(study.registry_ids),
            }
            for study in bundle.studies
        ]
        evidence_counts = {
            "pico": len(bundle.evidence_variables),
            "effects": len(bundle.evidence),
            "adverse_events": len(bundle.adverse_events),
            "eligibility": len(bundle.eligibility),
        }
        gaps = detect_gaps(bundle)
        freshness = {
            "studies": len(studies),
            "latest_study": max((study.study_id for study in bundle.studies), default=None),
        }
        return {
            "studies": studies,
            "evidence_counts": evidence_counts,
            "gaps": gaps,
            "freshness": freshness,
        }

    def qa(self, topic: Topic, query: str) -> QAResult:
        bundle = self._repository.load_topic_bundle(topic)
        return self._qa_engine.answer(query, bundle)

    def _build_payload(self, bundle: TopicBundle) -> dict[str, object]:
        self._citations.validate(
            [
                [citation for citation in item.citations]
                for iterable in (
                    bundle.studies,
                    bundle.evidence_variables,
                    bundle.evidence,
                    bundle.adverse_events,
                    bundle.doses,
                    bundle.eligibility,
                    bundle.guidelines,
                )
                for item in iterable
            ]
        )
        sections: list[dict[str, object]] = [
            {"title": "PICO", "items": _simplify(build_pico(bundle))},
            {"title": "Endpoints", "items": build_endpoint_summary(bundle)},
            {"title": "Safety", "items": build_safety_profile(bundle)},
            {"title": "Dosing", "items": build_dosing(bundle)},
            {"title": "Eligibility", "items": build_eligibility(bundle)},
            {"title": "Guidelines", "items": build_guideline_summary(bundle)},
        ]
        bibliography = self._citations.bibliography(bundle.all_citations())
        return {
            "topic": f"{bundle.topic.condition} / {bundle.topic.intervention} / {bundle.topic.outcome}",
            "sections": sections,
            "bibliography": bibliography,
        }

    def _render(self, payload: Mapping[str, object], format: str) -> object:
        if format == "json":
            return self._formatter.to_json(payload)
        if format == "md":
            return self._formatter.to_markdown(payload)
        if format == "html":
            return self._formatter.to_html(payload)
        if format == "pdf":
            return self._formatter.to_pdf(payload)
        if format == "docx":
            return self._formatter.to_docx(payload)
        raise ValueError(f"Unsupported format: {format}")


def _simplify(
    pico_sections: Mapping[str, Sequence[Mapping[str, object]]],
) -> list[dict[str, object]]:
    items: list[dict[str, object]] = []
    for section, entries in pico_sections.items():
        for entry in entries:
            description = entry.get("description", "")
            citations = entry.get("citations", [])
            citations_list: list[object]
            if isinstance(citations, list):
                citations_list = citations
            else:
                citations_list = []
            items.append(
                {
                    "summary": f"{section}: {description}",
                    "citations": citations_list,
                }
            )
    return items


def _priority_sort_key(item: Mapping[str, Any]) -> int:
    value = item.get("priority")
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return 0


__all__ = ["BriefingService", "BriefingSettings"]
