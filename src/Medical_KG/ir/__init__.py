"""Intermediate representation (IR) normalization utilities."""

from .models import Block, DocumentIR, SpanMap, Table
from .normalizer import NormalizedText, TextNormalizer
from .validator import IRValidator, ValidationError

__all__ = [
    "Block",
    "DocumentIR",
    "SpanMap",
    "Table",
    "NormalizedText",
    "TextNormalizer",
    "IRValidator",
    "ValidationError",
]
