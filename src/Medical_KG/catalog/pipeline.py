"""Catalog build pipeline orchestrating loaders, normalisation, and embeddings."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, List, Mapping, MutableMapping, Sequence

if TYPE_CHECKING:  # pragma: no cover
    from Medical_KG.embeddings.service import EmbeddingService

import yaml

from .loaders import ConceptLoader
from .models import Concept
from .normalization import ConceptNormaliser
from .state import CatalogStateStore


@dataclass(slots=True)
class LicensePolicy:
    """License gating based on entitlement flags per bucket."""

    entitlements: Mapping[str, bool]
    disabled_loaders: frozenset[str] = frozenset()

    @classmethod
    def permissive(cls) -> "LicensePolicy":
        return cls({"open": True, "permissive": True, "restricted": True, "proprietary": True})

    @classmethod
    def public(cls) -> "LicensePolicy":
        return cls({"open": True, "permissive": True, "restricted": False, "proprietary": False})

    @classmethod
    def from_file(cls, path: str | Path) -> "LicensePolicy":
        """Load entitlements and loader overrides from a YAML configuration file."""

        data = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
        buckets = data.get("buckets", {})
        entitlements = {
            "open": bool(buckets.get("open", True)),
            "permissive": bool(buckets.get("permissive", True)),
            "restricted": bool(buckets.get("restricted", False)),
            "proprietary": bool(buckets.get("proprietary", False)),
        }
        loader_rules = data.get("loaders", {})
        disabled = {
            str(name).upper()
            for name, config in loader_rules.items()
            if not bool((config or {}).get("enabled", False))
        }
        return cls(entitlements=entitlements, disabled_loaders=frozenset(disabled))

    def is_loader_enabled(self, loader: ConceptLoader) -> bool:
        if loader.ontology.upper() in self.disabled_loaders:
            return False
        return self.entitlements.get(loader.license_bucket, False)

    def filter_concepts(self, concepts: Iterable[Concept]) -> List[Concept]:
        return [
            concept
            for concept in concepts
            if self.entitlements.get(concept.license_bucket, False)
            and concept.ontology.upper() not in self.disabled_loaders
        ]


@dataclass(slots=True)
class CatalogAuditLog:
    """Collects audit entries for catalog operations."""

    entries: List[Mapping[str, object]] = field(default_factory=list)

    def record(
        self, action: str, *, user: str, resource: str, metadata: Mapping[str, object] | None = None
    ) -> None:
        payload = {"action": action, "user": user, "resource": resource}
        if metadata:
            payload.update(metadata)
        self.entries.append(payload)


@dataclass(slots=True)
class CatalogBuildResult:
    """Result of running the catalog build pipeline."""

    concepts: List[Concept]
    release_hash: str
    synonym_catalog: Mapping[str, List[str]]
    audit_log: CatalogAuditLog
    release_versions: Mapping[str, str]
    changed_ontologies: set[str]
    skipped: bool = False


class CatalogReleaseHasher:
    """Compute a deterministic release hash for catalog snapshots."""

    def compute(self, concepts: Sequence[Concept]) -> str:
        digest = hashlib.sha256()
        for concept in sorted(
            concepts,
            key=lambda c: (
                c.ontology,
                next(iter(sorted(c.codes.items())), ("", c.iri))[1],
            ),
        ):
            digest.update(concept.iri.encode("utf-8"))
            digest.update(json.dumps(concept.release, sort_keys=True).encode("utf-8"))
            digest.update(json.dumps(concept.codes, sort_keys=True).encode("utf-8"))
        return digest.hexdigest()


class CrosswalkBuilder:
    """Build crosswalk relationships across ontologies."""

    def apply(self, concepts: Sequence[Concept]) -> None:
        cui_groups: MutableMapping[str, set[str]] = {}
        code_groups: MutableMapping[str, set[str]] = {}
        for concept in concepts:
            cui = concept.attributes.get("umls_cui") if concept.attributes else None
            if cui:
                cui_groups.setdefault(str(cui), set()).add(concept.iri)
            for system, code in concept.codes.items():
                key = f"{system}:{code}"
                code_groups.setdefault(key, set()).add(concept.iri)
            for system, values in concept.xrefs.items():
                for value in values:
                    key = f"{system}:{value}"
                    code_groups.setdefault(key, set()).add(concept.iri)
        for group in list(cui_groups.values()) + list(code_groups.values()):
            if len(group) <= 1:
                continue
            for concept in concepts:
                if concept.iri in group:
                    for iri in group:
                        concept.ensure_same_as(iri)


class ConceptDeduplicator:
    """Deduplicate concepts by label and definition."""

    def deduplicate(self, concepts: Iterable[Concept]) -> List[Concept]:
        deduped: MutableMapping[tuple[str, str | None], Concept] = {}
        for concept in concepts:
            key = (concept.label.lower(), concept.definition)
            if key in deduped:
                deduped[key].merge(concept)
            else:
                deduped[key] = concept
        return list(deduped.values())


class ConceptCatalogBuilder:
    """High-level orchestrator for building the concept catalog."""

    def __init__(
        self,
        loaders: Sequence[ConceptLoader],
        *,
        license_policy: LicensePolicy | None = None,
        embedding_service: EmbeddingService | None = None,
        state_store: CatalogStateStore | None = None,
    ) -> None:
        self._loaders = list(loaders)
        self._license_policy = license_policy or LicensePolicy.permissive()
        self._normaliser = ConceptNormaliser()
        self._deduplicator = ConceptDeduplicator()
        self._crosswalk_builder = CrosswalkBuilder()
        self._hasher = CatalogReleaseHasher()
        self._embedding_service = embedding_service
        self._state_store = state_store

    def build(self) -> CatalogBuildResult:
        concepts: List[Concept] = []
        audit_log = CatalogAuditLog()
        release_versions: dict[str, str] = {}
        for loader in self._loaders:
            if not self._license_policy.is_loader_enabled(loader):
                audit_log.record(
                    "loader.skipped",
                    user="catalog",
                    resource=loader.ontology,
                    metadata={"reason": "license", "license_bucket": loader.license_bucket},
                )
                continue
            for concept in loader.load():
                audit_log.record(
                    "concept.loaded",
                    user="catalog",
                    resource=concept.iri,
                    metadata={"ontology": concept.ontology},
                )
                concepts.append(self._normaliser.normalise(concept))
            release_versions[loader.ontology] = loader.release_version
        deduped = self._deduplicator.deduplicate(concepts)
        self._crosswalk_builder.apply(deduped)
        release_hash = self._hasher.compute(deduped)
        synonym_catalog = self._normaliser.aggregate_synonyms(deduped)
        changed_ontologies: set[str]
        skipped = False
        if self._state_store:
            previous_hash = self._state_store.get_release_hash()
            previous_versions = self._state_store.get_release_versions()
            if previous_hash == release_hash:
                skipped = True
                changed_ontologies = set()
            else:
                changed_ontologies = {
                    ontology
                    for ontology, version in release_versions.items()
                    if previous_versions.get(ontology) != version
                }
                if not changed_ontologies:
                    changed_ontologies = set(release_versions)
        else:
            changed_ontologies = set(release_versions)
        if not skipped and self._embedding_service:
            self._embedding_service.embed_concepts(deduped)
        if self._state_store and not skipped:
            self._state_store.set_release_hash(release_hash)
            self._state_store.set_release_versions(release_versions)
        return CatalogBuildResult(
            concepts=deduped,
            release_hash=release_hash,
            synonym_catalog=synonym_catalog,
            audit_log=audit_log,
            release_versions=release_versions,
            changed_ontologies=changed_ontologies,
            skipped=skipped,
        )


__all__ = [
    "CatalogAuditLog",
    "CatalogBuildResult",
    "ConceptCatalogBuilder",
    "CatalogReleaseHasher",
    "CrosswalkBuilder",
    "LicensePolicy",
]
