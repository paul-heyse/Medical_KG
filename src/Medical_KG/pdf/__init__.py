"""PDF MinerU pipeline."""

from .gpu import GpuNotAvailableError, detect_gpu, ensure_gpu
from .mineru import MinerUArtifacts, MinerUConfig, MinerURunner, MinerURunResult
from .postprocess import (
    HeaderFooterSuppressor,
    HyphenationRepair,
    SectionLabeler,
    TextBlock,
    TwoColumnReflow,
)
from .qa import QaGateError, QaGates, QaMetrics
from .service import ArtifactStore, LocalArtifactStore, PdfDocument, PdfPipeline

__all__ = [
    "ensure_gpu",
    "detect_gpu",
    "GpuNotAvailableError",
    "MinerURunner",
    "MinerUConfig",
    "MinerURunResult",
    "MinerUArtifacts",
    "PdfPipeline",
    "PdfDocument",
    "ArtifactStore",
    "LocalArtifactStore",
    "QaGates",
    "QaGateError",
    "QaMetrics",
    "TextBlock",
    "TwoColumnReflow",
    "HeaderFooterSuppressor",
    "HyphenationRepair",
    "SectionLabeler",
]
