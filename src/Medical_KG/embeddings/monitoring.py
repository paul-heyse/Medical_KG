"""Performance monitoring utilities for GPU embedding services."""

from __future__ import annotations

import itertools
import statistics
import subprocess
import time
from dataclasses import dataclass, field
from typing import Mapping, Protocol, Sequence

from .gpu import GPURequirementError, GPUValidator
from .service import EmbeddingService


class AlertSink(Protocol):  # pragma: no cover - interface definition
    def emit(self, alert: str, message: str) -> None:
        """Record an alert event."""


@dataclass(slots=True)
class GPUStats:
    """Summarised GPU utilisation metrics."""

    utilisation: float
    memory_used_mb: float


@dataclass(slots=True)
class BenchmarkResult:
    """Result of a single embedding benchmark run."""

    throughput_per_minute: float
    dense_tokens_per_second: float
    sparse_terms_per_second: float
    batch_size: int
    duration_seconds: float


@dataclass(slots=True)
class LoadTestResult:
    """Result of a synthetic load test run."""

    total_chunks: int
    failed_chunks: int
    duration_seconds: float
    throughput_per_minute: float
    latency_p95_ms: float
    latency_samples_ms: list[float] = field(default_factory=list)


@dataclass(slots=True)
class EmbeddingPerformanceMonitor:
    """Coordinate benchmarking, health checks, and alerting for embeddings."""

    service: EmbeddingService
    gpu_validator: GPUValidator | None = None
    alert_sink: AlertSink | None = None

    def benchmark_embeddings(self, sample_texts: Sequence[str]) -> BenchmarkResult:
        """Run a single benchmark embedding call and capture throughput metrics."""

        if not sample_texts:
            return BenchmarkResult(0.0, 0.0, 0.0, 0, 0.0)
        start = time.perf_counter()
        self.service.embed_texts(sample_texts)
        duration = max(time.perf_counter() - start, 1e-6)
        throughput = (len(sample_texts) / duration) * 60.0
        metrics = self.service.metrics
        return BenchmarkResult(
            throughput_per_minute=throughput,
            dense_tokens_per_second=metrics.dense_tokens_per_second,
            sparse_terms_per_second=metrics.sparse_terms_per_second,
            batch_size=metrics.dense_batch_size,
            duration_seconds=duration,
        )

    def collect_gpu_stats(self) -> GPUStats:
        """Collect aggregate GPU utilisation metrics via nvidia-smi."""

        command = [
            "nvidia-smi",
            "--query-gpu=utilization.gpu,memory.used",
            "--format=csv,noheader,nounits",
        ]
        result = subprocess.run(  # pragma: no cover - executed via tests with monkeypatch
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=3,
        )
        rows = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if not rows:
            return GPUStats(utilisation=0.0, memory_used_mb=0.0)
        utilisations = []
        memories = []
        for row in rows:
            parts = [part.strip() for part in row.split(",") if part.strip()]
            if len(parts) >= 2:
                utilisations.append(float(parts[0]))
                memories.append(float(parts[1]))
        utilisation = sum(utilisations) / len(utilisations) if utilisations else 0.0
        memory = sum(memories) / len(memories) if memories else 0.0
        return GPUStats(utilisation=utilisation, memory_used_mb=memory)

    def monitor_health(self, *, endpoint: str | None = None) -> None:
        """Validate GPU and vLLM availability, emitting alerts on failure."""

        validator = self.gpu_validator or self.service.gpu_validator or GPUValidator()
        try:
            validator.validate()
            if endpoint:
                validator.validate_vllm(endpoint)
        except GPURequirementError as exc:  # pragma: no cover - tested via monkeypatch
            self._emit_alert("gpu_unavailable", str(exc))
            raise

    def check_throughput(self, benchmark: BenchmarkResult, *, threshold: float) -> None:
        """Emit alert when throughput drops below configured threshold."""

        if benchmark.throughput_per_minute < threshold:
            message = (
                f"Embedding throughput {benchmark.throughput_per_minute:.1f} chunks/min "
                f"below threshold {threshold:.1f}"
            )
            self._emit_alert("throughput_low", message)

    def run_load_test(
        self,
        sample_texts: Sequence[str],
        *,
        target_chunks: int = 10_000,
        batch_size: int | None = None,
    ) -> LoadTestResult:
        """Drive repeated embedding calls to estimate sustained throughput."""

        if not sample_texts:
            return LoadTestResult(0, 0, 0.0, 0.0, 0.0)
        batch = batch_size or getattr(self.service.qwen, "batch_size", 256)
        latencies: list[float] = []
        total = 0
        failed = 0
        start = time.perf_counter()
        iterator = itertools.cycle(sample_texts)
        while total < target_chunks:
            remaining = target_chunks - total
            current_batch_size = min(batch, remaining)
            batch_texts = [next(iterator) for _ in range(current_batch_size)]
            attempt_start = time.perf_counter()
            try:
                self.service.embed_texts(batch_texts)
                total += current_batch_size
            except Exception:  # pragma: no cover - surfaced in tests via monkeypatch
                failed += current_batch_size
            latency = (time.perf_counter() - attempt_start) * 1000.0
            latencies.append(latency)
        duration = max(time.perf_counter() - start, 1e-6)
        throughput = (total / duration) * 60.0 if duration else 0.0
        if latencies:
            if len(latencies) >= 2:
                p95 = statistics.quantiles(latencies, n=100, method="inclusive")[94]
            else:
                p95 = latencies[0]
        else:
            p95 = 0.0
        return LoadTestResult(
            total_chunks=total,
            failed_chunks=failed,
            duration_seconds=duration,
            throughput_per_minute=throughput,
            latency_p95_ms=p95,
            latency_samples_ms=latencies,
        )

    def dashboard_definition(self) -> Mapping[str, object]:
        """Return Grafana-style dashboard metadata for documentation/export."""

        return {
            "title": "Embedding GPU Performance",
            "panels": [
                {
                    "title": "Embedding Throughput",
                    "metric": "embedding_throughput_chunks_per_minute",
                    "description": "Chunks processed per minute from benchmark/load test",
                },
                {
                    "title": "GPU Utilisation",
                    "metric": "gpu_utilisation_percent",
                    "description": "Average GPU utilisation collected via nvidia-smi",
                },
                {
                    "title": "SPLADE Terms/sec",
                    "metric": "splade_terms_per_second",
                    "description": "Sparse expansion rate from embedding metrics",
                },
            ],
        }

    def _emit_alert(self, alert: str, message: str) -> None:
        if self.alert_sink:
            self.alert_sink.emit(alert, message)


__all__ = [
    "AlertSink",
    "BenchmarkResult",
    "EmbeddingPerformanceMonitor",
    "GPUStats",
    "LoadTestResult",
]
