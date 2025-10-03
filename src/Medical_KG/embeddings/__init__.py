"""Embedding utilities for dense and sparse retrieval."""

from .gpu import GPURequirementError, GPUValidator, enforce_gpu_or_exit
from .monitoring import (
    AlertSink,
    BenchmarkResult,
    EmbeddingPerformanceMonitor,
    GPUStats,
    LoadTestResult,
)
from .qwen import QwenEmbeddingClient
from .service import EmbeddingMetrics, EmbeddingService
from .splade import SPLADEExpander

__all__ = [
    "EmbeddingMetrics",
    "EmbeddingService",
    "AlertSink",
    "BenchmarkResult",
    "EmbeddingPerformanceMonitor",
    "GPURequirementError",
    "GPUStats",
    "GPUValidator",
    "LoadTestResult",
    "QwenEmbeddingClient",
    "SPLADEExpander",
    "enforce_gpu_or_exit",
]
