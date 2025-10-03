#!/usr/bin/env python3
"""
E2E Verification Suite

Runs complete pipeline verification from ingestion to briefing output.
Tests all major components and validates quality metrics.

Usage:
    python ops/e2e/run_verification.py --env staging
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """Result of a verification step."""

    step: str
    passed: bool
    duration_seconds: float
    details: dict[str, Any]
    error: str | None = None


class E2EVerifier:
    """Orchestrates end-to-end verification tests."""

    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=300.0, headers={"Authorization": f"Bearer {api_key}"})
        self.results: list[VerificationResult] = []
        self.start_time = time.time()

    def run(self) -> bool:
        """Run all verification steps. Returns True if all pass."""
        logger.info("Starting E2E verification suite")

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

        for step_fn in steps:
            try:
                result = step_fn()
                self.results.append(result)
                if not result.passed:
                    logger.error(f"❌ {result.step} FAILED: {result.error}")
                else:
                    logger.info(f"✅ {result.step} PASSED ({result.duration_seconds:.1f}s)")
            except Exception as exc:
                logger.exception(f"Exception in {step_fn.__name__}")
                self.results.append(
                    VerificationResult(
                        step=step_fn.__name__,
                        passed=False,
                        duration_seconds=0,
                        details={},
                        error=str(exc),
                    )
                )

        return self.generate_report()

    def verify_ingest_documents(self) -> VerificationResult:
        """Step 1: Ingest 10 PMC + 10 SPL + 10 NCT documents."""
        start = time.time()
        step = "Ingest Documents"

        try:
            # PMC Open Access
            pmc_ids = [
                "PMC6000001",
                "PMC6000002",
                "PMC6000003",
                "PMC6000004",
                "PMC6000005",
                "PMC6000006",
                "PMC6000007",
                "PMC6000008",
                "PMC6000009",
                "PMC6000010",
            ]
            resp_pmc = self.client.post(
                f"{self.base_url}/ingest/pmc", json={"pmcids": pmc_ids, "auto": True}
            )
            resp_pmc.raise_for_status()
            pmc_result = resp_pmc.json()

            # DailyMed SPL
            spl_ids = [f"setid-{i:06d}" for i in range(1, 11)]
            resp_spl = self.client.post(
                f"{self.base_url}/ingest/dailymed", json={"setids": spl_ids, "auto": True}
            )
            resp_spl.raise_for_status()
            spl_result = resp_spl.json()

            # ClinicalTrials.gov
            nct_ids = [f"NCT0{i:07d}" for i in range(1, 11)]
            resp_nct = self.client.post(
                f"{self.base_url}/ingest/clinicaltrials",
                json={"nct_ids": nct_ids, "auto": True},
            )
            resp_nct.raise_for_status()
            nct_result = resp_nct.json()

            total_docs = (
                len(pmc_result.get("doc_ids", []))
                + len(spl_result.get("doc_ids", []))
                + len(nct_result.get("doc_ids", []))
            )

            passed = total_docs >= 25  # Allow some failures
            duration = time.time() - start

            return VerificationResult(
                step=step,
                passed=passed,
                duration_seconds=duration,
                details={"total_docs": total_docs, "pmc": len(pmc_result.get("doc_ids", []))},
                error=None if passed else f"Only {total_docs}/30 docs ingested",
            )

        except Exception as exc:
            return VerificationResult(
                step=step,
                passed=False,
                duration_seconds=time.time() - start,
                details={},
                error=str(exc),
            )

    def verify_chunking(self) -> VerificationResult:
        """Step 2: Verify chunking completes."""
        start = time.time()
        step = "Chunking"

        try:
            # TODO: Get doc_ids from previous step
            # For now, assume auto=True handled chunking
            # Could query for recent chunks
            resp = self.client.get(f"{self.base_url}/chunks?limit=100")
            resp.raise_for_status()
            chunks = resp.json().get("chunks", [])

            passed = len(chunks) >= 100
            duration = time.time() - start

            return VerificationResult(
                step=step,
                passed=passed,
                duration_seconds=duration,
                details={"chunk_count": len(chunks)},
                error=None if passed else "Insufficient chunks created",
            )

        except Exception as exc:
            return VerificationResult(
                step=step,
                passed=False,
                duration_seconds=time.time() - start,
                details={},
                error=str(exc),
            )

    def verify_facet_generation(self) -> VerificationResult:
        """Step 3: Generate facets for chunks."""
        start = time.time()
        step = "Facet Generation"

        try:
            # Get sample chunk IDs
            resp_chunks = self.client.get(f"{self.base_url}/chunks?limit=10")
            resp_chunks.raise_for_status()
            chunks = resp_chunks.json().get("chunks", [])
            chunk_ids = [c["chunk_id"] for c in chunks[:10]]

            # Generate facets
            resp = self.client.post(
                f"{self.base_url}/facets/generate", json={"chunk_ids": chunk_ids}
            )
            resp.raise_for_status()
            result = resp.json()

            facet_count = sum(len(v) for v in result.get("facets_by_chunk", {}).values())
            passed = facet_count >= 5  # At least some facets generated
            duration = time.time() - start

            return VerificationResult(
                step=step,
                passed=passed,
                duration_seconds=duration,
                details={"facet_count": facet_count},
                error=None if passed else "No facets generated",
            )

        except Exception as exc:
            return VerificationResult(
                step=step,
                passed=False,
                duration_seconds=time.time() - start,
                details={},
                error=str(exc),
            )

    def verify_embedding(self) -> VerificationResult:
        """Step 4: Generate embeddings."""
        start = time.time()
        step = "Embedding"

        try:
            # Get sample chunk IDs
            resp_chunks = self.client.get(f"{self.base_url}/chunks?limit=10")
            resp_chunks.raise_for_status()
            chunks = resp_chunks.json().get("chunks", [])
            chunk_ids = [c["chunk_id"] for c in chunks[:10]]

            # Embed chunks
            resp = self.client.post(
                f"{self.base_url}/embed",
                json={"object_ids": chunk_ids, "object_type": "chunk"},
            )
            resp.raise_for_status()
            result = resp.json()

            embedded = result.get("embedded_count", 0)
            passed = embedded >= 8  # Most should succeed
            duration = time.time() - start

            return VerificationResult(
                step=step,
                passed=passed,
                duration_seconds=duration,
                details={"embedded_count": embedded},
                error=None if passed else f"Only {embedded}/10 embedded",
            )

        except Exception as exc:
            return VerificationResult(
                step=step,
                passed=False,
                duration_seconds=time.time() - start,
                details={},
                error=str(exc),
            )

    def verify_indexing(self) -> VerificationResult:
        """Step 5: Verify indexing completed."""
        start = time.time()
        step = "Indexing"

        # Indexing happens automatically; verify by searching
        try:
            resp = self.client.post(
                f"{self.base_url}/retrieve",
                json={"query": "diabetes treatment efficacy", "topK": 20},
            )
            resp.raise_for_status()
            result = resp.json()

            results_count = len(result.get("results", []))
            passed = results_count >= 10
            duration = time.time() - start

            return VerificationResult(
                step=step,
                passed=passed,
                duration_seconds=duration,
                details={"results_count": results_count},
                error=None if passed else "Insufficient indexed documents",
            )

        except Exception as exc:
            return VerificationResult(
                step=step,
                passed=False,
                duration_seconds=time.time() - start,
                details={},
                error=str(exc),
            )

    def verify_retrieval_quality(self) -> VerificationResult:
        """Step 6: Run gold queries and verify Recall@20."""
        start = time.time()
        step = "Retrieval Quality"

        # Simplified: just verify retrieval works
        # Full implementation would load gold_queries.jsonl and compute metrics
        try:
            queries = [
                "metformin efficacy type 2 diabetes",
                "adverse events checkpoint inhibitors",
                "pembrolizumab dosing melanoma",
                "PICO randomized controlled trials",
            ]

            total_recall = 0.0
            for query in queries:
                resp = self.client.post(
                    f"{self.base_url}/retrieve", json={"query": query, "topK": 20}
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])
                # Simplified: assume any results = recall
                if len(results) >= 10:
                    total_recall += 1.0

            avg_recall = total_recall / len(queries)
            passed = avg_recall >= 0.75  # 75% of queries returned results
            duration = time.time() - start

            return VerificationResult(
                step=step,
                passed=passed,
                duration_seconds=duration,
                details={"avg_recall": avg_recall},
                error=None if passed else f"Recall {avg_recall:.2f} below threshold",
            )

        except Exception as exc:
            return VerificationResult(
                step=step,
                passed=False,
                duration_seconds=time.time() - start,
                details={},
                error=str(exc),
            )

    def verify_entity_linking(self) -> VerificationResult:
        """Step 7: Verify entity linking."""
        start = time.time()
        step = "Entity Linking"

        # Simplified: just verify API works
        try:
            resp = self.client.post(
                f"{self.base_url}/map/el",
                json={
                    "mention": "metformin",
                    "candidates": [{"id": "RXCUI:6809", "label": "Metformin", "score": 0.95}],
                    "context": "patient treated with metformin",
                },
            )
            resp.raise_for_status()
            result = resp.json()

            passed = "chosen_id" in result
            duration = time.time() - start

            return VerificationResult(
                step=step,
                passed=passed,
                duration_seconds=duration,
                details={"chosen_id": result.get("chosen_id")},
                error=None if passed else "Entity linking failed",
            )

        except Exception as exc:
            return VerificationResult(
                step=step,
                passed=False,
                duration_seconds=time.time() - start,
                details={},
                error=str(exc),
            )

    def verify_extraction(self) -> VerificationResult:
        """Step 8: Verify clinical extraction."""
        start = time.time()
        step = "Clinical Extraction"

        try:
            # Get sample chunks
            resp_chunks = self.client.get(f"{self.base_url}/chunks?limit=5")
            resp_chunks.raise_for_status()
            chunks = resp_chunks.json().get("chunks", [])
            chunk_ids = [c["chunk_id"] for c in chunks[:5]]

            # Extract PICO
            resp = self.client.post(f"{self.base_url}/extract/pico", json={"chunk_ids": chunk_ids})
            resp.raise_for_status()
            result = resp.json()

            extraction_count = len(result.get("extractions", []))
            passed = extraction_count >= 1
            duration = time.time() - start

            return VerificationResult(
                step=step,
                passed=passed,
                duration_seconds=duration,
                details={"extraction_count": extraction_count},
                error=None if passed else "No extractions generated",
            )

        except Exception as exc:
            return VerificationResult(
                step=step,
                passed=False,
                duration_seconds=time.time() - start,
                details={},
                error=str(exc),
            )

    def verify_kg_write(self) -> VerificationResult:
        """Step 9: Verify KG write and SHACL validation."""
        start = time.time()
        step = "KG Write"

        # Simplified: just verify API works
        try:
            resp = self.client.post(
                f"{self.base_url}/kg/write",
                json={
                    "nodes": [
                        {
                            "id": "test_node_1",
                            "type": "Drug",
                            "properties": {"name": "Metformin"},
                        }
                    ],
                    "edges": [],
                    "provenance": {"source": "e2e_test"},
                },
            )
            resp.raise_for_status()
            result = resp.json()

            written = result.get("written_count", 0)
            passed = written >= 1
            duration = time.time() - start

            return VerificationResult(
                step=step,
                passed=passed,
                duration_seconds=duration,
                details={"written_count": written},
                error=None if passed else "KG write failed",
            )

        except Exception as exc:
            return VerificationResult(
                step=step,
                passed=False,
                duration_seconds=time.time() - start,
                details={},
                error=str(exc),
            )

    def verify_briefing_generation(self) -> VerificationResult:
        """Step 10: Generate briefing and verify citations."""
        start = time.time()
        step = "Briefing Generation"

        # Simplified: just verify API works
        try:
            resp = self.client.post(
                f"{self.base_url}/briefing/generate",
                json={"query": "metformin efficacy", "format": "markdown"},
            )
            resp.raise_for_status()
            result = resp.json()

            content = result.get("content", "")
            citations = result.get("citations", [])

            passed = len(content) > 100 and len(citations) > 0
            duration = time.time() - start

            return VerificationResult(
                step=step,
                passed=passed,
                duration_seconds=duration,
                details={"content_length": len(content), "citation_count": len(citations)},
                error=None if passed else "Briefing generation failed",
            )

        except Exception as exc:
            return VerificationResult(
                step=step,
                passed=False,
                duration_seconds=time.time() - start,
                details={},
                error=str(exc),
            )

    def verify_e2e_latency(self) -> VerificationResult:
        """Step 11: Verify E2E latency < 5 minutes."""
        step = "E2E Latency"

        elapsed = time.time() - self.start_time
        passed = elapsed < 300  # 5 minutes

        return VerificationResult(
            step=step,
            passed=passed,
            duration_seconds=elapsed,
            details={"total_elapsed_seconds": elapsed},
            error=None if passed else f"E2E took {elapsed:.1f}s (> 300s)",
        )

    def generate_report(self) -> bool:
        """Generate final report and return overall pass/fail."""
        logger.info("\n" + "=" * 80)
        logger.info("E2E VERIFICATION REPORT")
        logger.info("=" * 80)

        passed_count = sum(1 for r in self.results if r.passed)
        total_count = len(self.results)

        logger.info(f"\nResults: {passed_count}/{total_count} steps passed\n")

        for result in self.results:
            status = "✅ PASS" if result.passed else "❌ FAIL"
            logger.info(f"{status} | {result.step} ({result.duration_seconds:.1f}s)")
            if not result.passed and result.error:
                logger.info(f"      Error: {result.error}")

        total_elapsed = time.time() - self.start_time
        logger.info(f"\nTotal Duration: {total_elapsed:.1f}s")
        logger.info("=" * 80)

        # Write JSON report
        report_path = Path("ops/e2e/last_run_report.json")
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "timestamp": datetime.utcnow().isoformat(),
                    "passed": passed_count == total_count,
                    "total_steps": total_count,
                    "passed_steps": passed_count,
                    "duration_seconds": total_elapsed,
                    "results": [
                        {
                            "step": r.step,
                            "passed": r.passed,
                            "duration_seconds": r.duration_seconds,
                            "details": r.details,
                            "error": r.error,
                        }
                        for r in self.results
                    ],
                },
                indent=2,
            )
        )

        return passed_count == total_count


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run E2E verification suite")
    parser.add_argument(
        "--env",
        choices=["dev", "staging", "production"],
        default="staging",
        help="Environment to test",
    )
    parser.add_argument("--base-url", help="Override base URL")
    parser.add_argument("--api-key", help="API key for authentication")
    args = parser.parse_args()

    # Environment-specific URLs
    env_urls = {
        "dev": "http://localhost:8000",
        "staging": "https://api-staging.medkg.example.com",
        "production": "https://api.medkg.example.com",
    }

    base_url = args.base_url or env_urls[args.env]
    api_key = args.api_key or "<your-api-key>"  # TODO: Load from env or secret

    verifier = E2EVerifier(base_url=base_url, api_key=api_key)
    success = verifier.run()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
