"""Normalization utilities for concept ingestion."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Match

from .models import Concept, Synonym

_GREEK_MAP = {
    "α": "alpha",
    "β": "beta",
    "γ": "gamma",
    "δ": "delta",
    "ε": "epsilon",
    "θ": "theta",
    "λ": "lambda",
    "μ": "mu",
    "π": "pi",
    "σ": "sigma",
    "ω": "omega",
}

_US_UK_VARIANTS = {
    "anaemia": "anemia",
    "oedema": "edema",
    "oesophagus": "esophagus",
    "paediatric": "pediatric",
    "tumour": "tumor",
}

_SALT_PATTERN = re.compile(
    r"\b(?P<base>[A-Za-z]+) (?P<salt>hydrochloride|sodium|potassium|sulfate|maleate)\b",
    re.IGNORECASE,
)
_WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    """Apply Unicode normalisation, whitespace collapsing, and case folding for matching."""

    value = unicodedata.normalize("NFC", value.strip())
    value = _WHITESPACE_PATTERN.sub(" ", value)
    return value


def normalize_greek(value: str) -> str:
    """Replace inline Greek symbols with their latin names for lexical matching."""

    result = []
    for char in value:
        replacement = _GREEK_MAP.get(char, char)
        result.append(replacement)
    return normalize_text("".join(result))


def normalize_spelling(value: str) -> str:
    """Normalise well-known UK/US spelling variants by mapping to US spelling."""

    lower = value.lower()
    for variant, canonical in _US_UK_VARIANTS.items():
        lower = lower.replace(variant, canonical)
    return normalize_text(lower)


def recognise_salts(value: str) -> str:
    """Keep salt names while providing canonical representation for search."""

    def _replace(match: Match[str]) -> str:
        base = match.group("base")
        salt = match.group("salt")
        return f"{base} ({salt})"

    return _SALT_PATTERN.sub(_replace, value)


@dataclass(slots=True)
class ConceptNormaliser:
    """Normalise and enrich concept instances in-place."""

    def normalise(self, concept: Concept) -> Concept:
        concept.label = normalize_text(concept.label)
        concept.preferred_term = normalize_text(concept.preferred_term)
        if concept.definition:
            concept.definition = normalize_text(concept.definition)
        synonyms = []
        seen = set()
        for synonym in concept.synonyms:
            value = recognise_salts(normalize_greek(normalize_text(synonym.value)))
            canonical = normalize_spelling(value)
            if canonical.lower() in seen:
                continue
            seen.add(canonical.lower())
            synonyms.append(Synonym(value=canonical, type=synonym.type))
        concept.synonyms = synonyms
        return concept

    def aggregate_synonyms(self, concepts: Iterable[Concept]) -> dict[str, list[str]]:
        """Create mapping of ontology → sorted synonym list for downstream analyzers."""

        synonyms: dict[str, list[str]] = {}
        for concept in concepts:
            entries = {syn.value for syn in concept.synonyms}
            if entries:
                current = set(synonyms.get(concept.ontology, []))
                current.update(entries)
                synonyms[concept.ontology] = sorted(current)
        return synonyms

    def compute_synonym_statistics(self, concepts: Iterable[Concept]) -> dict[str, int]:
        """Return counts of synonym frequency for reporting."""

        counter: Counter[str] = Counter()
        for concept in concepts:
            counter.update(syn.value for syn in concept.synonyms)
        return dict(counter)


def merge_synonym_catalogs(*catalogs: Mapping[str, Iterable[str]]) -> dict[str, list[str]]:
    """Merge multiple ontology → synonym mappings."""

    merged: dict[str, list[str]] = {}
    for catalog in catalogs:
        for ontology, values in catalog.items():
            current = set(merged.get(ontology, []))
            current.update(values)
            merged[ontology] = sorted(current)
    return merged


__all__ = ["ConceptNormaliser", "merge_synonym_catalogs", "normalize_text"]
