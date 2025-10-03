from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from Medical_KG.embeddings.gpu import GPURequirementError, GPUValidator
from Medical_KG.embeddings.monitoring import (
    EmbeddingPerformanceMonitor,
    GPUStats,
    LoadTestResult,
)
from Medical_KG.embeddings.service import EmbeddingMetrics


class FakeService:
    def __init__(self) -> None:
        self.metrics = EmbeddingMetrics(
            dense_tokens_per_second=120.0,
            dense_batch_size=4,
            sparse_terms_per_second=90.0,
        )
        self.calls: list[list[str]] = []
        self.fail_next = False
        self.gpu_validator: GPUValidator | None = None

    def embed_texts(self, texts: list[str]) -> tuple[list[list[float]], list[dict[str, float]]]:
        self.calls.append(list(texts))
        if self.fail_next:
            self.fail_next = False
            raise RuntimeError("failure")
        return [[0.0] * 2 for _ in texts], [{} for _ in texts]


class RecordingSink:
    def __init__(self) -> None:
        self.alerts: list[tuple[str, str]] = []

    def emit(self, alert: str, message: str) -> None:
        self.alerts.append((alert, message))


def test_benchmark_embeddings_uses_service_metrics() -> None:
    service = FakeService()
    monitor = EmbeddingPerformanceMonitor(service)
    result = monitor.benchmark_embeddings(["alpha", "beta"])
    assert result.batch_size == service.metrics.dense_batch_size
    assert result.throughput_per_minute > 0


def test_collect_gpu_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):
        return SimpleNamespace(stdout="75, 1024\n60, 2048\n")

    monkeypatch.setattr(subprocess, "run", fake_run)
    monitor = EmbeddingPerformanceMonitor(FakeService())
    stats = monitor.collect_gpu_stats()
    assert isinstance(stats, GPUStats)
    assert stats.utilisation == pytest.approx(67.5)
    assert stats.memory_used_mb == pytest.approx(1536.0)


def test_monitor_health_emits_alert(monkeypatch: pytest.MonkeyPatch) -> None:
    service = FakeService()

    class Failing(GPUValidator):
        def validate(self) -> None:  # type: ignore[override]
            raise GPURequirementError("not available")

    sink = RecordingSink()
    monitor = EmbeddingPerformanceMonitor(service, gpu_validator=Failing(), alert_sink=sink)
    with pytest.raises(GPURequirementError):
        monitor.monitor_health()
    assert sink.alerts and sink.alerts[0][0] == "gpu_unavailable"


def test_run_load_test_records_latency(monkeypatch: pytest.MonkeyPatch) -> None:
    service = FakeService()
    monitor = EmbeddingPerformanceMonitor(service)
    result = monitor.run_load_test(["alpha", "beta"], target_chunks=4, batch_size=2)
    assert isinstance(result, LoadTestResult)
    assert result.total_chunks == 4
    assert result.latency_p95_ms >= 0


def test_check_throughput_triggers_alert() -> None:
    service = FakeService()
    sink = RecordingSink()
    monitor = EmbeddingPerformanceMonitor(service, alert_sink=sink)
    benchmark = monitor.benchmark_embeddings(["alpha"])
    monitor.check_throughput(benchmark, threshold=benchmark.throughput_per_minute * 2)
    assert sink.alerts and sink.alerts[0][0] == "throughput_low"


def test_dashboard_definition_structure() -> None:
    monitor = EmbeddingPerformanceMonitor(FakeService())
    dashboard = monitor.dashboard_definition()
    assert dashboard["title"] == "Embedding GPU Performance"
    assert len(dashboard["panels"]) == 3
