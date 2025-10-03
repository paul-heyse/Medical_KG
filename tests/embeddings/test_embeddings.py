from __future__ import annotations

import pytest

from Medical_KG.catalog.models import Concept, ConceptFamily
from Medical_KG.embeddings import (
    EmbeddingPerformanceMonitor,
    EmbeddingService,
    GPURequirementError,
    GPUStats,
    GPUValidator,
    LoadTestResult,
    QwenEmbeddingClient,
    SPLADEExpander,
    enforce_gpu_or_exit,
)


@pytest.fixture(autouse=True)
def reset_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("REQUIRE_GPU", raising=False)


def test_gpu_validator_skips_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REQUIRE_GPU", "0")
    validator = GPUValidator()
    validator.validate()  # does not raise


def test_gpu_validator_raises_without_gpu(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("REQUIRE_GPU", "1")
    validator = GPUValidator()
    with pytest.raises(GPURequirementError):
        validator.validate()


def test_qwen_embeddings_are_deterministic() -> None:
    client = QwenEmbeddingClient(dimension=8, batch_size=4)
    first = client.embed(["hello world"])[0]
    second = client.embed(["hello world"])[0]
    assert pytest.approx(first) == second
    norm = sum(value * value for value in first) ** 0.5
    assert pytest.approx(norm, rel=1e-6) == 1.0


def test_embedding_service_sets_vectors(monkeypatch: pytest.MonkeyPatch) -> None:
    concept = Concept(
        iri="http://example.org/concept/1",
        ontology="TEST",
        family=ConceptFamily.CONDITION,
        label="Example concept",
        preferred_term="Example concept",
        definition="A sample concept for testing.",
        synonyms=[],
        codes={"test": "1"},
        xrefs={},
        parents=[],
        ancestors=[],
        attributes={"umls_cui": "C000"},
        release={"version": "1", "released_at": "2025-01-01"},
        license_bucket="open",
        provenance={"source": "unit"},
    )
    service = EmbeddingService(
        qwen=QwenEmbeddingClient(dimension=8, batch_size=4), splade=SPLADEExpander(top_k=4)
    )
    service.embed_concepts([concept])
    assert concept.embedding_qwen is not None
    assert len(concept.embedding_qwen) == 8
    assert concept.splade_terms


def test_qwen_client_http_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    class DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict[str, object]:
            return {"data": [{"embedding": [0.1, 0.2]}]}

    class DummyClient:
        def __init__(self) -> None:
            self.calls = 0

        def post(self, url: str, json: dict[str, object]) -> DummyResponse:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("transient error")
            return DummyResponse()

        def close(self) -> None:
            return None

    factory_client = DummyClient()

    def factory() -> DummyClient:
        return factory_client

    client = QwenEmbeddingClient(
        dimension=2, batch_size=8, api_url="http://fake", http_client_factory=factory
    )
    vectors = client.embed(["text"])
    assert len(vectors[0]) == 2
    assert factory_client.calls == 2


def test_enforce_gpu_or_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingValidator(GPUValidator):
        def validate(self) -> None:  # type: ignore[override]
            raise GPURequirementError("missing gpu")

    with pytest.raises(SystemExit) as excinfo:
        enforce_gpu_or_exit(validator=FailingValidator())
    assert excinfo.value.code == 99


class RecordingSink:
    def __init__(self) -> None:
        self.alerts: list[tuple[str, str]] = []

    def emit(self, alert: str, message: str) -> None:
        self.alerts.append((alert, message))


def test_embedding_monitor_benchmark_and_alerts() -> None:
    service = EmbeddingService(
        qwen=QwenEmbeddingClient(dimension=8, batch_size=4), splade=SPLADEExpander(top_k=4)
    )
    sink = RecordingSink()
    monitor = EmbeddingPerformanceMonitor(service, alert_sink=sink)
    result = monitor.benchmark_embeddings(["alpha", "beta", "gamma"])
    assert result.throughput_per_minute > 0
    monitor.check_throughput(result, threshold=result.throughput_per_minute * 2)
    assert sink.alerts and sink.alerts[0][0] == "throughput_low"


def test_embedding_monitor_collects_gpu_stats(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(*args, **kwargs):
        class Result:
            stdout = "75, 1024\n60, 2048\n"

        return Result()

    monkeypatch.setattr(
        "Medical_KG.embeddings.monitoring.subprocess.run", fake_run
    )
    service = EmbeddingService(
        qwen=QwenEmbeddingClient(dimension=8, batch_size=4), splade=SPLADEExpander(top_k=4)
    )
    monitor = EmbeddingPerformanceMonitor(service)
    stats = monitor.collect_gpu_stats()
    assert isinstance(stats, GPUStats)
    assert stats.utilisation == pytest.approx(67.5)
    assert stats.memory_used_mb == pytest.approx(1536.0)


def test_embedding_monitor_load_test_and_health(monkeypatch: pytest.MonkeyPatch) -> None:
    class FailingValidator(GPUValidator):
        def validate(self) -> None:  # type: ignore[override]
            raise GPURequirementError("not visible")

    service = EmbeddingService(
        qwen=QwenEmbeddingClient(dimension=8, batch_size=2), splade=SPLADEExpander(top_k=4)
    )
    sink = RecordingSink()
    monitor = EmbeddingPerformanceMonitor(service, gpu_validator=FailingValidator(), alert_sink=sink)
    result = monitor.run_load_test(["alpha", "beta"], target_chunks=4, batch_size=2)
    assert isinstance(result, LoadTestResult)
    assert result.total_chunks == 4
    assert result.throughput_per_minute > 0
    with pytest.raises(GPURequirementError):
        monitor.monitor_health()
    assert any(alert for alert, _ in sink.alerts if alert == "gpu_unavailable")
    dashboard = monitor.dashboard_definition()
    assert dashboard["title"] == "Embedding GPU Performance"
