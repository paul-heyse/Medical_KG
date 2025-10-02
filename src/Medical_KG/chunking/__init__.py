"""Semantic chunking utilities."""

from .chunker import Chunk, SemanticChunker, select_profile
from .document import Document, Section, Table
from .facets import FacetGenerator
from .metrics import ChunkMetrics, compute_metrics
from .pipeline import ChunkingPipeline, ChunkingResult
from .profiles import PROFILES, ChunkingProfile, get_profile
from .tagger import ClinicalIntent, ClinicalIntentTagger

__all__ = [
    "Chunk",
    "ChunkMetrics",
    "ChunkingPipeline",
    "ChunkingProfile",
    "ChunkingResult",
    "ClinicalIntent",
    "ClinicalIntentTagger",
    "Document",
    "FacetGenerator",
    "PROFILES",
    "Section",
    "SemanticChunker",
    "Table",
    "compute_metrics",
    "get_profile",
    "select_profile",
]
