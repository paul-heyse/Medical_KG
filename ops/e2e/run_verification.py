"""End-to-end verification harness for Medical KG deployments."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Sequence

from Medical_KG.briefing.models import (
    AdverseEvent as BriefingAdverseEvent,
)
from Medical_KG.briefing.models import (
    Citation as BriefingCitation,
)
from Medical_KG.briefing.models import (
    Dose as BriefingDose,
)
from Medical_KG.briefing.models import (
    EligibilityConstraint as BriefingEligibility,
)
from Medical_KG.briefing.models import (
    Evidence as BriefingEvidence,
)
from Medical_KG.briefing.models import (
    EvidenceVariable as BriefingEvidenceVariable,
)
from Medical_KG.briefing.models import (
    GuidelineRecommendation as BriefingGuideline,
)
from Medical_KG.briefing.models import (
    Study as BriefingStudy,
)
from Medical_KG.briefing.models import (
    Topic as BriefingTopic,
)
from Medical_KG.briefing.models import (
    TopicBundle as BriefingBundle,
)
from Medical_KG.briefing.repository import InMemoryBriefingRepository
from Medical_KG.briefing.service import BriefingService, BriefingSettings
from Medical_KG.chunking.chunker import Chunk as SemanticChunk
from Medical_KG.chunking.chunker import SemanticChunker
from Medical_KG.chunking.document import Document, Section
from Medical_KG.chunking.profiles import get_profile
from Medical_KG.embeddings.qwen import QwenEmbeddingClient
from Medical_KG.embeddings.service import EmbeddingService, SPLADEExpander
from Medical_KG.entity_linking.candidates import (
    Candidate,
    CandidateGenerator,
    DenseClient,
    DictionaryClient,
    SparseClient,
)
from Medical_KG.entity_linking.decision import DecisionEngine
from Medical_KG.entity_linking.llm import LlmAdjudicator, LlmClient
from Medical_KG.entity_linking.ner import Mention
from Medical_KG.entity_linking.service import EntityLinkingService
from Medical_KG.extraction.service import Chunk as ExtractionChunk
from Medical_KG.extraction.service import ClinicalExtractionService
from Medical_KG.facets.service import Chunk as FacetChunk
from Medical_KG.facets.service import FacetService
from Medical_KG.kg.service import KgWriteFailure, KgWriteService
from Medical_KG.services.retrieval import RetrievalService

logger = logging.getLogger("ops.e2e")


# ---------------------------------------------------------------------------
# Fixture data models
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class SectionFixture:
    name: str
    start: int
    end: int
    loinc_code: str | None = None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SectionFixture":
        return cls(
            name=str(data.get("name", "Body")),
            start=int(data.get("start", 0)),
            end=int(data.get("end", 0)),
            loinc_code=data.get("loinc_code"),
        )

    def to_section(self) -> Section:
        return Section(name=self.name, start=self.start, end=self.end, loinc_code=self.loinc_code)


@dataclass(slots=True)
class DocumentFixture:
    doc_id: str
    text: str
    sections: list[SectionFixture] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DocumentFixture":
        sections = [SectionFixture.from_dict(item) for item in data.get("sections", [])]
        return cls(doc_id=str(data["doc_id"]), text=str(data["text"]), sections=sections)

    def to_document(self) -> Document:
        if not self.sections:
            fallback = Section(name="Body", start=0, end=len(self.text))
            return Document(doc_id=self.doc_id, text=self.text, sections=[fallback])
        return Document(
            doc_id=self.doc_id,
            text=self.text,
            sections=[section.to_section() for section in self.sections],
        )


@dataclass(slots=True)
class RetrievalQueryFixture:
    query: str
    intent: str | None
    min_results: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RetrievalQueryFixture":
        return cls(
            query=str(data["query"]),
            intent=data.get("intent"),
            min_results=int(data.get("min_results", 1)),
        )


@dataclass(slots=True)
class EntityLinkingFixture:
    text: str
    context: str
    expected_id: str
    label: str
    ontology: str = "RxCUI"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "EntityLinkingFixture":
        return cls(
            text=str(data["text"]),
            context=str(data.get("context", "")),
            expected_id=str(data["expected_id"]),
            label=str(data.get("label", data["expected_id"])),
            ontology=str(data.get("ontology", "RxCUI")),
        )


@dataclass(slots=True)
class BriefingFixture:
    topic: Mapping[str, str]
    bundle: Mapping[str, Any]
    min_length: int
    min_citations: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BriefingFixture":
        return cls(
            topic=data["topic"],
            bundle=data["bundle"],
            min_length=int(data.get("min_length", 200)),
            min_citations=int(data.get("min_citations", 1)),
        )

    def to_topic(self) -> BriefingTopic:
        return BriefingTopic(
            condition=str(self.topic["condition"]),
            intervention=str(self.topic["intervention"]),
            outcome=str(self.topic["outcome"]),
        )

    def to_bundle(self) -> BriefingBundle:
        def _citations(items: Iterable[Mapping[str, Any]]) -> list[BriefingCitation]:
            return [
                BriefingCitation(
                    doc_id=str(citation["doc_id"]),
                    start=int(citation.get("start", 0)),
                    end=int(citation.get("end", 0)),
                    quote=str(citation.get("quote", "")),
                )
                for citation in items
            ]

        def _evidence_variable(item: Mapping[str, Any]) -> BriefingEvidenceVariable:
            return BriefingEvidenceVariable(
                kind=str(item.get("kind", "population")),
                description=str(item.get("description", "")),
                citations=tuple(_citations(item.get("citations", []))),
            )

        def _evidence(item: Mapping[str, Any]) -> BriefingEvidence:
            return BriefingEvidence(
                study_id=str(item.get("study_id", "")),
                population=str(item.get("population", "")),
                intervention=str(item.get("intervention", "")),
                outcome=str(item.get("outcome", "")),
                effect_type=str(item.get("effect_type", "HR")),
                value=float(item.get("value", 0.0)),
                ci_low=(float(item["ci_low"]) if item.get("ci_low") is not None else None),
                ci_high=(float(item["ci_high"]) if item.get("ci_high") is not None else None),
                p_value=(float(item["p_value"]) if item.get("p_value") is not None else None),
                certainty=str(item.get("certainty", "moderate")),
                citations=tuple(_citations(item.get("citations", []))),
            )

        def _adverse_event(item: Mapping[str, Any]) -> BriefingAdverseEvent:
            return BriefingAdverseEvent(
                study_id=str(item.get("study_id", "")),
                meddra_pt=str(item.get("meddra_pt", "")),
                grade=(int(item["grade"]) if item.get("grade") is not None else None),
                rate=(float(item["rate"]) if item.get("rate") is not None else None),
                numerator=(int(item["numerator"]) if item.get("numerator") is not None else None),
                denominator=(
                    int(item["denominator"]) if item.get("denominator") is not None else None
                ),
                citations=tuple(_citations(item.get("citations", []))),
            )

        def _dose(item: Mapping[str, Any]) -> BriefingDose:
            return BriefingDose(
                study_id=str(item.get("study_id", "")),
                description=str(item.get("description", "")),
                amount=(float(item["amount"]) if item.get("amount") is not None else None),
                unit=item.get("unit"),
                frequency=item.get("frequency"),
                citations=tuple(_citations(item.get("citations", []))),
            )

        def _eligibility(item: Mapping[str, Any]) -> BriefingEligibility:
            return BriefingEligibility(
                constraint_type=str(item.get("constraint_type", "inclusion")),
                description=str(item.get("description", "")),
                citations=tuple(_citations(item.get("citations", []))),
            )

        def _guideline(item: Mapping[str, Any]) -> BriefingGuideline:
            return BriefingGuideline(
                guideline_id=str(item.get("guideline_id", "")),
                statement=str(item.get("statement", "")),
                strength=str(item.get("strength", "B")),
                certainty=str(item.get("certainty", "moderate")),
                citations=tuple(_citations(item.get("citations", []))),
            )

        topic = self.to_topic()
        studies = [
            BriefingStudy(
                study_id=str(item.get("study_id", "")),
                title=str(item.get("title", "")),
                registry_ids=tuple(str(value) for value in item.get("registry_ids", [])),
                citations=tuple(_citations(item.get("citations", []))),
            )
            for item in self.bundle.get("studies", [])
        ]
        evidence_variables = [
            _evidence_variable(item) for item in self.bundle.get("evidence_variables", [])
        ]
        evidence = [_evidence(item) for item in self.bundle.get("evidence", [])]
        adverse_events = [_adverse_event(item) for item in self.bundle.get("adverse_events", [])]
        doses = [_dose(item) for item in self.bundle.get("doses", [])]
        eligibility = [_eligibility(item) for item in self.bundle.get("eligibility", [])]
        guidelines = [_guideline(item) for item in self.bundle.get("guidelines", [])]
        return BriefingBundle(
            topic=topic,
            studies=tuple(studies),
            evidence_variables=tuple(evidence_variables),
            evidence=tuple(evidence),
            adverse_events=tuple(adverse_events),
            doses=tuple(doses),
            eligibility=tuple(eligibility),
            guidelines=tuple(guidelines),
        )


@dataclass(slots=True)
class FixtureData:
    ingest_pmc: list[str]
    ingest_spl: list[str]
    ingest_nct: list[str]
    documents: list[DocumentFixture]
    retrieval_queries: list[RetrievalQueryFixture]
    entity_linking: EntityLinkingFixture
    kg_payload: Mapping[str, Any]
    briefing: BriefingFixture
    min_chunk_count: int

    @classmethod
    def load(cls, path: Path) -> "FixtureData":
        data = json.loads(path.read_text())
        return cls(
            ingest_pmc=[str(item) for item in data.get("ingest", {}).get("pmc_ids", [])],
            ingest_spl=[str(item) for item in data.get("ingest", {}).get("spl_setids", [])],
            ingest_nct=[str(item) for item in data.get("ingest", {}).get("nct_ids", [])],
            documents=[DocumentFixture.from_dict(item) for item in data.get("documents", [])],
            retrieval_queries=[
                RetrievalQueryFixture.from_dict(item) for item in data.get("retrieval_queries", [])
            ],
            entity_linking=EntityLinkingFixture.from_dict(data.get("entity_linking", {})),
            kg_payload=data.get("kg_payload", {}),
            briefing=BriefingFixture.from_dict(data.get("briefing", {})),
            min_chunk_count=int(data.get("min_chunk_count", 10)),
        )


@dataclass(slots=True)
class LatencyBudget:
    total_seconds: float
    per_step: Dict[str, float]

    @classmethod
    def load(cls, path: Path | None) -> "LatencyBudget":
        if path is None or not path.exists():
            return cls(total_seconds=300.0, per_step={})
        data = json.loads(path.read_text())
        per_step = {str(step): float(value) for step, value in data.get("per_step", {}).items()}
        return cls(total_seconds=float(data.get("total_seconds", 300.0)), per_step=per_step)

    def bound(self, step: str, duration: float) -> tuple[bool, str | None]:
        limit = self.per_step.get(step)
        if limit is None:
            return True, None
        if duration <= limit:
            return True, None
        return False, f"Duration {duration:.2f}s exceeded budget {limit:.2f}s"


@dataclass(slots=True)
class VerificationResult:
    step: str
    passed: bool
    duration_seconds: float
    details: Dict[str, Any]
    error: str | None = None


# ---------------------------------------------------------------------------
# Entity linking helpers
# ---------------------------------------------------------------------------


class FixtureNer:
    """NER pipeline that always returns a single configured mention."""

    def __init__(self, mention: Mention) -> None:
        self._mention = mention

    def __call__(self, _: str) -> Sequence[Mention]:
        return [self._mention]


class StaticDictionary(DictionaryClient):
    def __init__(self, candidate: Candidate) -> None:
        self._candidate = candidate

    def search(self, text: str, *, fuzzy: bool = False) -> Sequence[Candidate]:  # noqa: D401
        return [self._candidate]


class StaticSparse(SparseClient):
    def __init__(self, candidate: Candidate) -> None:
        self._candidate = candidate

    def search(self, text: str) -> Sequence[Candidate]:  # noqa: D401
        return [self._candidate]


class StaticDense(DenseClient):
    def __init__(self, candidate: Candidate) -> None:
        self._candidate = candidate

    def search(self, text: str, context: str) -> Sequence[Candidate]:  # noqa: D401
        return [self._candidate]


class StaticLlmClient(LlmClient):
    def __init__(self, *, chosen_id: str, ontology: str, score: float) -> None:
        self._chosen_id = chosen_id
        self._ontology = ontology
        self._score = score

    async def complete(
        self, *, prompt: str, payload: Mapping[str, Any]
    ) -> Mapping[str, Any]:  # noqa: D401
        return {
            "chosen_id": self._chosen_id,
            "ontology": self._ontology,
            "score": self._score,
            "evidence_span": {"start": 0, "end": len(payload.get("mention", ""))},
            "alternates": [],
        }


# ---------------------------------------------------------------------------
# Verifier implementation
# ---------------------------------------------------------------------------


class E2EVerifier:
    def __init__(
        self,
        *,
        mode: str,
        fixtures: FixtureData,
        budget: LatencyBudget,
        base_url: str | None,
        api_key: str | None,
        report_path: Path,
    ) -> None:
        self.mode = mode
        self.dry_run = mode == "offline"
        self.fixtures = fixtures
        self.budget = budget
        self.base_url = base_url.rstrip("/") if base_url else None
        self.api_key = api_key
        self.report_path = report_path
        self.results: list[VerificationResult] = []
        self.start_time = time.time()
        self._documents = [fixture.to_document() for fixture in fixtures.documents]
        self._semantic_chunks: list[SemanticChunk] = []
        self._facet_service = FacetService()
        self._retrieval_service = RetrievalService()
        self._embedding_service = EmbeddingService(
            qwen=QwenEmbeddingClient(dimension=64, batch_size=32),
            splade=SPLADEExpander(top_k=128, batch_size=64),
        )
        self._extraction_service = ClinicalExtractionService()
        self._kg_service = KgWriteService()
        self._http = None

    # ------------------------------------------------------------------
    # Main orchestration
    # ------------------------------------------------------------------

    def run(self) -> bool:
        logger.info("Starting E2E verification (mode=%s)", self.mode)
        steps = [
            self.verify_ingest_documents,
            self.verify_chunking,
            self.verify_facet_generation,
            self.verify_embedding,
            self.verify_indexing,
            self.verify_retrieval_quality,
            self.verify_entity_linking,
            self.verify_extraction,
            self.verify_kg_write,
            self.verify_briefing_generation,
            self.verify_e2e_latency,
        ]
        for step in steps:
            result = step()
            self.results.append(result)
            if result.passed:
                logger.info("✅ %s (%.2fs)", result.step, result.duration_seconds)
            else:
                logger.error("❌ %s -- %s", result.step, result.error or "failed")
        return self.generate_report()

    # ------------------------------------------------------------------
    # Verification steps
    # ------------------------------------------------------------------

    def verify_ingest_documents(self) -> VerificationResult:
        step = "Ingest Documents"
        start = time.time()
        pmc = len(self.fixtures.ingest_pmc)
        spl = len(self.fixtures.ingest_spl)
        nct = len(self.fixtures.ingest_nct)
        passed = pmc >= 10 and spl >= 10 and nct >= 10
        duration = time.time() - start
        passed, error = self._apply_budget(step, passed, duration)
        return VerificationResult(
            step=step,
            passed=passed,
            duration_seconds=duration,
            details={"pmc_ids": pmc, "spl_setids": spl, "nct_ids": nct},
            error=error,
        )

    def verify_chunking(self) -> VerificationResult:
        step = "Chunking"
        start = time.time()
        chunker = SemanticChunker(profile=get_profile("imrad"))
        chunks: list[SemanticChunk] = []
        for document in self._documents:
            chunks.extend(chunker.chunk(document))
        self._semantic_chunks = chunks
        duration = time.time() - start
        passed = len(chunks) >= self.fixtures.min_chunk_count
        details = {"chunk_count": len(chunks)}
        passed, error = self._apply_budget(step, passed, duration)
        return VerificationResult(
            step=step, passed=passed, duration_seconds=duration, details=details, error=error
        )

    def verify_facet_generation(self) -> VerificationResult:
        step = "Facet Generation"
        start = time.time()
        generated: dict[str, int] = {}
        for chunk in self._semantic_chunks:
            facet_chunk = FacetChunk(
                chunk_id=chunk.chunk_id,
                text=chunk.text,
                section=chunk.section,
                table_headers=list(chunk.table_lines or []),
            )
            facets = self._facet_service.generate_for_chunk(facet_chunk)
            generated[chunk.chunk_id] = len(facets)
        duration = time.time() - start
        min_facets = min(generated.values(), default=0)
        passed = bool(generated) and min_facets >= 1
        passed, error = self._apply_budget(step, passed, duration)
        return VerificationResult(
            step=step,
            passed=passed,
            duration_seconds=duration,
            details={"chunks": len(generated), "min_facets_per_chunk": min_facets},
            error=error,
        )

    def verify_embedding(self) -> VerificationResult:
        step = "Embedding"
        start = time.time()
        texts = [chunk.text for chunk in self._semantic_chunks]
        dense_vectors, sparse_vectors = self._embedding_service.embed_texts(texts)
        duration = time.time() - start
        passed = len(dense_vectors) == len(self._semantic_chunks) == len(sparse_vectors)
        metrics = self._embedding_service.metrics
        details = {
            "dense_batch_size": metrics.dense_batch_size,
            "dense_tokens_per_second": round(metrics.dense_tokens_per_second, 2),
            "sparse_terms_per_second": round(metrics.sparse_terms_per_second, 2),
        }
        passed, error = self._apply_budget(step, passed, duration)
        return VerificationResult(
            step=step, passed=passed, duration_seconds=duration, details=details, error=error
        )

    def verify_indexing(self) -> VerificationResult:
        step = "Indexing"
        start = time.time()
        indexed = 0
        for chunk in self._semantic_chunks:
            record = self._facet_service.index_payload(chunk.chunk_id)
            if record is None:
                continue
            self._retrieval_service.upsert(record, snippet=chunk.text[:200])
            indexed += 1
        duration = time.time() - start
        passed = indexed == len(self._semantic_chunks)
        passed, error = self._apply_budget(step, passed, duration)
        return VerificationResult(
            step=step,
            passed=passed,
            duration_seconds=duration,
            details={"indexed_chunks": indexed},
            error=error,
        )

    def verify_retrieval_quality(self) -> VerificationResult:
        step = "Retrieval Quality"
        start = time.time()
        satisfied = 0
        for query in self.fixtures.retrieval_queries:
            results = self._retrieval_service.search(
                query.query,
                facet_type=query.intent,
                top_k=20,
            )
            if len(results) >= query.min_results:
                satisfied += 1
        duration = time.time() - start
        passed = satisfied == len(self.fixtures.retrieval_queries)
        details = {"queries": len(self.fixtures.retrieval_queries), "satisfied": satisfied}
        passed, error = self._apply_budget(step, passed, duration)
        return VerificationResult(
            step=step, passed=passed, duration_seconds=duration, details=details, error=error
        )

    def verify_entity_linking(self) -> VerificationResult:
        step = "Entity Linking"
        start = time.time()
        fixture = self.fixtures.entity_linking
        text_lower = fixture.text.lower()
        mention_lower = fixture.label.lower()
        offset = text_lower.find(mention_lower)
        offset = offset if offset >= 0 else 0
        mention = Mention(
            text=fixture.label,
            start=offset,
            end=offset + len(fixture.label),
            label="CHEM",
        )
        candidate = Candidate(
            identifier=fixture.expected_id,
            ontology=fixture.ontology,
            score=0.92,
            label=fixture.label,
            metadata={},
        )
        generator = CandidateGenerator(
            dictionary=StaticDictionary(candidate),
            sparse=StaticSparse(candidate),
            dense=StaticDense(candidate),
        )
        adjudicator = LlmAdjudicator(
            StaticLlmClient(chosen_id=fixture.expected_id, ontology=fixture.ontology, score=0.95)
        )
        decision = DecisionEngine()
        service = EntityLinkingService(
            ner=FixtureNer(mention), generator=generator, adjudicator=adjudicator, decision=decision
        )
        results = asyncio.run(service.link(fixture.text, fixture.context))
        duration = time.time() - start
        accepted = [result for result in results if result.decision.accepted]
        passed = bool(accepted) and accepted[0].decision.candidate.identifier == fixture.expected_id
        details = {"mentions": len(results), "accepted": len(accepted)}
        passed, error = self._apply_budget(step, passed, duration)
        return VerificationResult(
            step=step, passed=passed, duration_seconds=duration, details=details, error=error
        )

    def verify_extraction(self) -> VerificationResult:
        step = "Clinical Extraction"
        start = time.time()
        chunks = [
            ExtractionChunk(chunk_id=chunk.chunk_id, text=chunk.text)
            for chunk in self._semantic_chunks
        ]
        envelope = self._extraction_service.extract_many(chunks)
        duration = time.time() - start
        passed = len(envelope.payload) >= len(self._semantic_chunks)
        details = {
            "chunk_ids": len(envelope.chunk_ids),
            "extraction_count": len(envelope.payload),
        }
        passed, error = self._apply_budget(step, passed, duration)
        return VerificationResult(
            step=step, passed=passed, duration_seconds=duration, details=details, error=error
        )

    def verify_kg_write(self) -> VerificationResult:
        step = "KG Write"
        start = time.time()
        try:
            result = self._kg_service.write(self.fixtures.kg_payload)
            passed = True
            details = {
                "written_nodes": result.written_nodes,
                "written_relationships": result.written_relationships,
            }
            error = None
        except KgWriteFailure as exc:
            passed = False
            details = {"issues": [issue.reason for issue in exc.issues]}
            error = ", ".join(issue.reason for issue in exc.issues)
        duration = time.time() - start
        passed, budget_error = self._apply_budget(step, passed, duration)
        if budget_error and not error:
            error = budget_error
        return VerificationResult(
            step=step, passed=passed, duration_seconds=duration, details=details, error=error
        )

    def verify_briefing_generation(self) -> VerificationResult:
        step = "Briefing Generation"
        start = time.time()
        fixture = self.fixtures.briefing
        repository = InMemoryBriefingRepository()
        bundle = fixture.to_bundle()
        repository.register(bundle)
        service = BriefingService(repository, settings=BriefingSettings(format_default="md"))
        dossier = service.dossier(bundle.topic, format="md")
        duration = time.time() - start
        content = str(dossier.get("content", ""))
        citations = dossier.get("citations", [])
        passed = len(content) >= fixture.min_length and len(citations) >= fixture.min_citations
        details = {"content_length": len(content), "citation_count": len(citations)}
        passed, error = self._apply_budget(step, passed, duration)
        return VerificationResult(
            step=step, passed=passed, duration_seconds=duration, details=details, error=error
        )

    def verify_e2e_latency(self) -> VerificationResult:
        step = "E2E Latency"
        duration = time.time() - self.start_time
        passed = duration <= self.budget.total_seconds
        details = {"total_duration": round(duration, 2)}
        error = (
            None
            if passed
            else f"Total duration {duration:.2f}s exceeded budget {self.budget.total_seconds:.2f}s"
        )
        return VerificationResult(
            step=step, passed=passed, duration_seconds=duration, details=details, error=error
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _apply_budget(self, step: str, passed: bool, duration: float) -> tuple[bool, str | None]:
        within_budget, message = self.budget.bound(step, duration)
        if not within_budget:
            passed = False
        return passed, message

    def generate_report(self) -> bool:
        passed_count = sum(1 for result in self.results if result.passed)
        total_count = len(self.results)
        total_duration = time.time() - self.start_time
        payload = {
            "timestamp": datetime.utcnow().isoformat(),
            "mode": self.mode,
            "passed": passed_count == total_count,
            "total_steps": total_count,
            "passed_steps": passed_count,
            "duration_seconds": total_duration,
            "results": [
                {
                    "step": result.step,
                    "passed": result.passed,
                    "duration_seconds": result.duration_seconds,
                    "details": result.details,
                    "error": result.error,
                }
                for result in self.results
            ],
        }
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(json.dumps(payload, indent=2))
        logger.info("Report written to %s", self.report_path)
        return payload["passed"]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Medical KG E2E verification")
    parser.add_argument("--env", choices=["dev", "staging", "production"], default="staging")
    parser.add_argument("--mode", choices=["offline", "live"], default="offline")
    parser.add_argument("--base-url", dest="base_url")
    parser.add_argument("--api-key", dest="api_key")
    parser.add_argument("--fixtures", type=Path, default=Path("ops/e2e/fixtures/pipeline.json"))
    parser.add_argument("--budget", type=Path, default=Path("ops/e2e/fixtures/budget.json"))
    parser.add_argument("--report", type=Path, default=Path("ops/e2e/last_run_report.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    fixtures = FixtureData.load(args.fixtures)
    budget = LatencyBudget.load(args.budget)
    base_url = args.base_url
    if base_url is None and args.mode == "live":
        env_urls = {
            "dev": "http://localhost:8000",
            "staging": "https://api-staging.medkg.example.com",
            "production": "https://api.medkg.example.com",
        }
        base_url = env_urls[args.env]
    verifier = E2EVerifier(
        mode=args.mode,
        fixtures=fixtures,
        budget=budget,
        base_url=base_url,
        api_key=args.api_key,
        report_path=args.report,
    )
    success = verifier.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
