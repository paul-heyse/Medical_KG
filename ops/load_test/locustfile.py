#!/usr/bin/env python3
"""
Load Testing Suite using Locust

Simulates realistic traffic patterns to verify system performance under load.

Usage:
    # Burst scenario (50 QPS for 2 minutes)
    locust -f ops/load_test/locustfile.py --headless \
        --users 50 --spawn-rate 10 --run-time 2m \
        --host https://api-staging.medkg.example.com

    # Steady scenario (10 QPS for 1 hour)
    locust -f ops/load_test/locustfile.py --headless \
        --users 10 --spawn-rate 2 --run-time 1h \
        --host https://api-staging.medkg.example.com
"""

from __future__ import annotations

import random

from typing import Callable

try:
    from locust import HttpUser, between, task
except Exception as exc:  # pragma: no cover - locust is optional during tests
    raise RuntimeError("locust must be installed to run load tests") from exc


class MedicalKGUser(HttpUser):
    """Simulates a user making requests to Medical KG API."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    def on_start(self) -> None:
        """Called when a simulated user starts."""
        # TODO: Replace with actual API key
        self.api_key = "test-api-key"
        self.client.headers.update({"Authorization": f"Bearer {self.api_key}"})

    # Task weights reflect realistic intent distribution
    @task(40)  # 40% of requests
    def retrieve_endpoint(self) -> None:
        """Retrieve endpoint-focused query."""
        queries = [
            "hazard ratio pembrolizumab melanoma",
            "overall survival nivolumab lung cancer",
            "progression free survival duration",
            "endpoint outcome randomized trial",
            "efficacy metformin diabetes",
        ]
        query = random.choice(queries)

        self.client.post(
            "/retrieve",
            json={"query": query, "intent": "endpoint", "topK": 20, "rerank_enabled": True},
            name="/retrieve [endpoint]",
        )

    @task(25)  # 25% of requests
    def retrieve_adverse_events(self) -> None:
        """Retrieve adverse events query."""
        queries = [
            "adverse events checkpoint inhibitors",
            "grade 3 toxicity pembrolizumab",
            "serious adverse reactions immunotherapy",
            "side effects metformin gastrointestinal",
            "hypoglycemia insulin therapy",
        ]
        query = random.choice(queries)

        self.client.post(
            "/retrieve",
            json={"query": query, "intent": "ae", "topK": 20, "rerank_enabled": True},
            name="/retrieve [ae]",
        )

    @task(15)  # 15% of requests
    def retrieve_dose(self) -> None:
        """Retrieve dosing information query."""
        queries = [
            "pembrolizumab 200mg dosing schedule",
            "metformin starting dose titration",
            "insulin dosage adjustment guidelines",
            "chemotherapy dosing body surface area",
        ]
        query = random.choice(queries)

        self.client.post(
            "/retrieve",
            json={"query": query, "intent": "dose", "topK": 20, "rerank_enabled": False},
            name="/retrieve [dose]",
        )

    @task(10)  # 10% of requests
    def retrieve_eligibility(self) -> None:
        """Retrieve eligibility criteria query."""
        queries = [
            "inclusion criteria melanoma trial",
            "exclusion pregnancy lactation",
            "eligibility age kidney function",
            "patient selection criteria immunotherapy",
        ]
        query = random.choice(queries)

        self.client.post(
            "/retrieve",
            json={"query": query, "intent": "eligibility", "topK": 20},
            name="/retrieve [eligibility]",
        )

    @task(10)  # 10% of requests
    def retrieve_general(self) -> None:
        """General medical query (no specific intent)."""
        queries = [
            "diabetes management guidelines",
            "cancer immunotherapy mechanisms",
            "clinical trial design randomization",
            "pharmacokinetics drug interactions",
        ]
        query = random.choice(queries)

        self.client.post(
            "/retrieve",
            json={"query": query, "topK": 20, "rerank_enabled": True},
            name="/retrieve [general]",
        )

    @task(5)
    def extract_pico(self) -> None:
        """Extract PICO from chunks."""
        # Simplified: use fixed chunk IDs for load testing
        chunk_ids = [f"chunk_{random.randint(1000, 9999)}" for _ in range(3)]

        self.client.post(
            "/extract/pico",
            json={"chunk_ids": chunk_ids},
            name="/extract/pico",
        )

    @task(3)
    def extract_effects(self) -> None:
        """Extract effects from chunks."""
        chunk_ids = [f"chunk_{random.randint(1000, 9999)}" for _ in range(3)]

        self.client.post(
            "/extract/effects",
            json={"chunk_ids": chunk_ids},
            name="/extract/effects",
        )

    @task(2)
    def facets_generate(self) -> None:
        """Generate facets for chunks."""
        chunk_ids = [f"chunk_{random.randint(1000, 9999)}" for _ in range(5)]

        self.client.post(
            "/facets/generate",
            json={"chunk_ids": chunk_ids},
            name="/facets/generate",
        )

    @task(1)
    def get_health(self) -> None:
        """Health check endpoint."""
        self.client.get("/health", name="/health")

    @task(1)
    def get_version(self) -> None:
        """Version endpoint."""
        self.client.get("/version", name="/version")


class BurstLoadUser(MedicalKGUser):
    """User for burst load testing (high concurrency)."""

    wait_time = between(0.5, 1.5)  # Faster requests


class SteadyLoadUser(MedicalKGUser):
    """User for steady load testing (realistic usage)."""

    wait_time = between(2, 5)  # Slower, more realistic


# For running different scenarios:
# Burst: Use BurstLoadUser with high user count
# Steady: Use SteadyLoadUser with lower user count
