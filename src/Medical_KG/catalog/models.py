"""Core catalog models with strict typing."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import cast

from .types import JsonValue


class ConceptFamily(str, Enum):
    """Enumeration of supported concept families."""

    CONDITION = "condition"
    PHENOTYPE = "phenotype"
    LAB = "lab"
    DRUG = "drug"
    SUBSTANCE = "substance"
    OUTCOME = "outcome"
    ADVERSE_EVENT = "adverse_event"
    DEVICE = "device"
    LITERATURE_ID = "literature_id"


class SynonymType(str, Enum):
    """Enumeration of synonym relationship types."""

    EXACT = "exact"
    NARROW = "narrow"
    BROAD = "broad"
    RELATED = "related"
    BRAND = "brand"
    ABBREV = "abbrev"


@dataclass(slots=True)
class Synonym:
    """Synonym entry for a concept."""

    value: str
    type: SynonymType

    def __post_init__(self) -> None:
        value = self.value.strip()
        if not value:
            msg = "synonym value must not be empty"
            raise ValueError(msg)
        self.value = value


@dataclass(slots=True)
class Concept:
    """Unified representation of a medical concept."""

    iri: str
    ontology: str
    family: ConceptFamily
    label: str
    preferred_term: str
    definition: str | None = None
    synonyms: list[Synonym] = field(default_factory=list)
    codes: dict[str, str] = field(default_factory=dict)
    xrefs: dict[str, list[str]] = field(default_factory=dict)
    parents: list[str] = field(default_factory=list)
    ancestors: list[str] = field(default_factory=list)
    same_as: list[str] = field(default_factory=list)
    attributes: dict[str, JsonValue] = field(default_factory=dict)
    semantic_types: list[str] = field(default_factory=list)
    status: str = "active"
    retired_date: str | None = None
    embedding_qwen: list[float] | None = None
    splade_terms: dict[str, float] | None = None
    release: dict[str, str] = field(default_factory=dict)
    license_bucket: str = "open"
    provenance: dict[str, JsonValue] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.iri = self._validate_iri(self.iri)
        self.label = self._require(self.label, "label")
        self.preferred_term = self._require(self.preferred_term, "preferred_term")
        self.definition = (
            self.definition.strip() if isinstance(self.definition, str) else self.definition
        )
        self.synonyms = [
            syn if isinstance(syn, Synonym) else Synonym(**syn) for syn in self.synonyms
        ]
        self.codes = {str(system): str(code) for system, code in self.codes.items()}
        self.xrefs = {
            system: [str(value) for value in values] for system, values in self.xrefs.items()
        }
        self.parents = [str(parent) for parent in self.parents]
        self.ancestors = [str(ancestor) for ancestor in self.ancestors]
        self.same_as = [str(iri) for iri in self.same_as]
        self.attributes = {str(key): value for key, value in self.attributes.items()}
        self.semantic_types = [str(value) for value in self.semantic_types]
        self.embedding_qwen = list(self.embedding_qwen) if self.embedding_qwen else None
        self.splade_terms = dict(self.splade_terms) if self.splade_terms else None
        self.release = {str(key): str(value) for key, value in self.release.items()}
        self.provenance = {str(key): value for key, value in self.provenance.items()}
        self.status = self._validate_status(self.status)
        self.license_bucket = self._validate_license(self.license_bucket)

    @staticmethod
    def _validate_iri(value: str) -> str:
        if not value.startswith(("http://", "https://")):
            msg = "iri must be an HTTP(S) URL"
            raise ValueError(msg)
        return value

    @staticmethod
    def _require(value: str, field_name: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            msg = f"{field_name} must not be empty"
            raise ValueError(msg)
        return trimmed

    @staticmethod
    def _validate_license(value: str) -> str:
        allowed = {"open", "permissive", "restricted", "proprietary"}
        if value not in allowed:
            msg = f"license_bucket must be one of {sorted(allowed)}"
            raise ValueError(msg)
        return value

    @staticmethod
    def _validate_status(value: str) -> str:
        allowed = {"active", "retired", "deprecated"}
        if value not in allowed:
            msg = "status must be active|retired|deprecated"
            raise ValueError(msg)
        return value

    def add_synonym(self, synonym: Synonym) -> None:
        """Add a synonym while avoiding duplicates."""

        if synonym not in self.synonyms:
            self.synonyms.append(synonym)

    def extend_synonyms(self, synonyms: Iterable[Synonym]) -> None:
        """Add multiple synonyms while keeping uniqueness."""

        for synonym in synonyms:
            self.add_synonym(synonym)

    def ensure_same_as(self, iri: str) -> None:
        """Add an equivalent IRI to the SAME_AS list."""

        if iri == self.iri:
            return
        if iri not in self.same_as:
            self.same_as.append(iri)

    def to_embedding_text(self) -> str:
        """Create canonical text used for embedding generation."""

        parts = [self.label]
        if self.definition:
            parts.append(self.definition)
        if self.synonyms:
            parts.append(", ".join(sorted({syn.value for syn in self.synonyms})))
        return " \n".join(parts)

    def merge(self, other: Concept) -> None:
        """Merge another concept representation into this one."""

        if self.ontology != other.ontology:
            self.ensure_same_as(other.iri)
        for synonym in other.synonyms:
            self.add_synonym(synonym)
        for system, code in other.codes.items():
            self.codes.setdefault(system, code)
        for key, values in other.xrefs.items():
            current = set(self.xrefs.get(key, []))
            current.update(values)
            self.xrefs[key] = sorted(current)
        for parent in other.parents:
            if parent not in self.parents:
                self.parents.append(parent)
        for ancestor in other.ancestors:
            if ancestor not in self.ancestors:
                self.ancestors.append(ancestor)
        for semantic in other.semantic_types:
            if semantic not in self.semantic_types:
                self.semantic_types.append(semantic)
        if other.definition and not self.definition:
            self.definition = other.definition
        if other.status == "retired":
            self.status = "retired"
            self.retired_date = other.retired_date or self.retired_date
        self.ensure_same_as(other.iri)

    def as_dict(self) -> dict[str, JsonValue]:
        """Serialise concept to a JSON-compatible dictionary."""

        payload = asdict(self)
        return cast(dict[str, JsonValue], payload)


@dataclass(slots=True)
class ConceptSchemaValidator:
    """Lightweight structural validator for concept instances."""

    required_fields: tuple[str, ...] = (
        "iri",
        "ontology",
        "family",
        "label",
        "preferred_term",
        "codes",
        "xrefs",
        "parents",
        "ancestors",
        "attributes",
        "license_bucket",
        "provenance",
    )

    @classmethod
    def create(cls) -> ConceptSchemaValidator:
        return cls()

    def validate(self, concept: Concept) -> None:
        payload = concept.as_dict()
        missing = [field for field in self.required_fields if field not in payload]
        if missing:
            msg = f"concept missing required fields: {', '.join(missing)}"
            raise ValueError(msg)
        bucket = payload.get("license_bucket")
        if bucket not in {"open", "permissive", "restricted", "proprietary"}:
            msg = "invalid license bucket"
            raise ValueError(msg)
        synonyms = payload.get("synonyms")
        if not isinstance(synonyms, list):
            msg = "synonyms must be a list"
            raise ValueError(msg)


__all__ = [
    "Concept",
    "ConceptFamily",
    "ConceptSchemaValidator",
    "Synonym",
    "SynonymType",
]
