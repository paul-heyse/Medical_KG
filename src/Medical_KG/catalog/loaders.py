"""Ontology loaders for the concept catalog (simplified for unit testing)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping, Sequence
from datetime import date
from typing import NotRequired, TypedDict

from .models import Concept, ConceptFamily, Synonym, SynonymType
from .types import JsonValue


class SnomedRF2Record(TypedDict):
    conceptId: str | int
    fsn: str
    preferred: NotRequired[str]
    definition: NotRequired[str]
    synonyms: NotRequired[Sequence[str]]
    parents: NotRequired[Sequence[str | int]]
    ancestors: NotRequired[Sequence[str | int]]
    icd10: NotRequired[Sequence[str | int]]
    active: NotRequired[bool]


class ICD11Entry(TypedDict):
    code: str
    title: str
    preferred: NotRequired[str]
    definition: NotRequired[str]
    parents: NotRequired[Sequence[str]]
    synonyms: NotRequired[Sequence[str]]
    snomed: NotRequired[Sequence[str | int]]
    api_version: NotRequired[str]


class MONDONode(TypedDict):
    id: str
    label: str
    preferred: NotRequired[str]
    definition: NotRequired[str]
    synonyms: NotRequired[Sequence[str]]
    xrefs: NotRequired[Mapping[str, Sequence[str | int]]]
    format: NotRequired[str]


class HPONode(TypedDict):
    id: str
    label: str
    preferred: NotRequired[str]
    definition: NotRequired[str]
    synonyms: NotRequired[Sequence[str]]
    diseases: NotRequired[Sequence[str | int]]
    format: NotRequired[str]


class LOINCRow(TypedDict):
    loinc_num: str | int
    component: NotRequired[str]
    property: NotRequired[str]
    shortname: NotRequired[str]
    long_common_name: NotRequired[str]
    system: NotRequired[str]
    scale: NotRequired[str]
    method: NotRequired[str]
    ucum_unit: NotRequired[str]


class RxNormConcept(TypedDict):
    rxcui: str | int
    name: str
    definition: NotRequired[str]
    synonyms: NotRequired[Sequence[str]]
    tty: NotRequired[str]
    ingredients: NotRequired[Sequence[str | int]]
    snomed: NotRequired[Sequence[str | int]]


class UNIIEntry(TypedDict):
    unii: str
    substance_name: str
    synonyms: NotRequired[Sequence[str]]
    preferred_term: NotRequired[str]


class MedDRARow(TypedDict):
    code: str
    pt: str
    level: NotRequired[str]
    definition: NotRequired[str]
    llt: NotRequired[Sequence[str]]
    soc: NotRequired[str]
    parents: NotRequired[Sequence[str | int]]


class CTCAERow(TypedDict):
    meddra_code: str
    term: str
    description: NotRequired[str]
    grade: NotRequired[int | str]
    synonyms: NotRequired[Sequence[str]]


class GUDIDDevice(TypedDict):
    di: str
    brand_name: str
    device_name: NotRequired[str]
    catalog_number: NotRequired[str]
    version: NotRequired[str]
    model_number: NotRequired[str]
    synonyms: NotRequired[Sequence[str]]


def _default_release(version: str) -> dict[str, str]:
    return {"version": version, "released_at": date.today().isoformat()}


class ConceptLoader(ABC):
    """Abstract base class for ontology loaders."""

    ontology: str
    family: ConceptFamily
    license_bucket: str
    loader_version: str = "0.1.0"

    def __init__(self, *, release_version: str | None = None) -> None:
        self._release = _default_release(release_version or "unversioned")

    @abstractmethod
    def load(self) -> Iterable[Concept]:
        """Yield normalised concepts."""

    @property
    def release_version(self) -> str:
        return self._release["version"]

    def _build(
        self,
        *,
        iri: str,
        label: str,
        preferred_term: str,
        definition: str | None,
        synonyms: Sequence[tuple[str, SynonymType]],
        codes: Mapping[str, str],
        parents: Sequence[str] | None = None,
        ancestors: Sequence[str] | None = None,
        xrefs: Mapping[str, Sequence[str]] | None = None,
        attributes: Mapping[str, JsonValue] | None = None,
        semantic_types: Sequence[str] | None = None,
        status: str = "active",
        provenance: Mapping[str, JsonValue] | None = None,
    ) -> Concept:
        synonyms_models = [Synonym(value=value, type=s_type) for value, s_type in synonyms if value]
        concept = Concept(
            iri=iri,
            ontology=self.ontology,
            family=self.family,
            label=label,
            preferred_term=preferred_term,
            definition=definition,
            synonyms=synonyms_models,
            codes=dict(codes),
            parents=list(parents or []),
            ancestors=list(ancestors or []),
            xrefs={key: list(values) for key, values in (xrefs or {}).items()},
            attributes=dict(attributes or {}),
            semantic_types=list(semantic_types or []),
            status=status,
            release=self._release,
            license_bucket=self.license_bucket,
            provenance={
                "source": self.ontology,
                "loader_version": self.loader_version,
                **(dict(provenance or {})),
            },
        )
        return concept


class SnomedCTLoader(ConceptLoader):
    """Simplified loader for SNOMED CT RF2 data."""

    ontology = "SNOMED"
    family = ConceptFamily.CONDITION
    license_bucket = "restricted"

    def __init__(
        self, records: Sequence[SnomedRF2Record], *, release_version: str = "2025-01-31"
    ) -> None:
        super().__init__(release_version=release_version)
        self._records = list(records)

    def load(self) -> Iterable[Concept]:
        for record in self._records:
            concept_id = str(record["conceptId"])
            iri = f"http://snomed.info/id/{concept_id}"
            label = str(record["fsn"])
            preferred = str(record.get("preferred", label))
            definition = record.get("definition")
            synonym_values = record.get("synonyms") or []
            synonyms = [(syn, SynonymType.EXACT) for syn in synonym_values]
            parents = [
                f"http://snomed.info/id/{pid}"
                for pid in (record.get("parents") or [])
            ]
            ancestors = [
                f"http://snomed.info/id/{aid}"
                for aid in (record.get("ancestors") or [])
            ]
            xrefs = {"icd10": [str(code) for code in (record.get("icd10") or [])]}
            attributes = {"active": bool(record.get("active", True))}
            status = "active" if attributes["active"] else "retired"
            yield self._build(
                iri=iri,
                label=label,
                preferred_term=preferred,
                definition=str(definition) if definition else None,
                synonyms=synonyms,
                codes={"snomed": concept_id},
                parents=parents,
                ancestors=ancestors,
                xrefs=xrefs,
                attributes=attributes,
                status=status,
                provenance={"rf2_release": self._release["version"]},
            )


class ICD11Loader(ConceptLoader):
    """Simplified loader for the ICD-11 API output."""

    ontology = "ICD11"
    family = ConceptFamily.CONDITION
    license_bucket = "permissive"

    def __init__(
        self, entries: Sequence[ICD11Entry], *, release_version: str = "2025"
    ) -> None:
        super().__init__(release_version=release_version)
        self._entries = list(entries)

    def load(self) -> Iterable[Concept]:
        for entry in self._entries:
            code = str(entry["code"])
            iri = f"https://id.who.int/icd/release/11/{code}"
            title = str(entry["title"])
            definition = entry.get("definition")
            parents = [
                f"https://id.who.int/icd/release/11/{parent}"
                for parent in (entry.get("parents") or [])
            ]
            synonym_values = entry.get("synonyms") or []
            synonyms = [(syn, SynonymType.RELATED) for syn in synonym_values]
            xrefs = {"snomed": [str(code) for code in (entry.get("snomed") or [])]}
            yield self._build(
                iri=iri,
                label=title,
                preferred_term=str(entry.get("preferred", title)),
                definition=str(definition) if definition else None,
                synonyms=synonyms,
                codes={"icd11": code},
                parents=parents,
                ancestors=[],
                xrefs=xrefs,
                semantic_types=["Clinical finding"],
                provenance={"api_version": entry.get("api_version", "v1")},
            )


class MONDOLoader(ConceptLoader):
    """Loader for MONDO disease ontology."""

    ontology = "MONDO"
    family = ConceptFamily.CONDITION
    license_bucket = "open"

    def __init__(
        self, nodes: Sequence[MONDONode], *, release_version: str = "2025-02"
    ) -> None:
        super().__init__(release_version=release_version)
        self._nodes = list(nodes)

    def load(self) -> Iterable[Concept]:
        for node in self._nodes:
            identifier = str(node["id"])
            iri = f"http://purl.obolibrary.org/obo/{identifier.replace(':', '_')}"
            label = str(node["label"])
            definition = node.get("definition")
            synonyms = [(syn, SynonymType.RELATED) for syn in (node.get("synonyms") or [])]
            mappings = node.get("xrefs") or {}
            yield self._build(
                iri=iri,
                label=label,
                preferred_term=str(node.get("preferred", label)),
                definition=str(definition) if definition else None,
                synonyms=synonyms,
                codes={"mondo": identifier},
                xrefs={key: list(map(str, values)) for key, values in mappings.items()},
                semantic_types=["Disease or Syndrome"],
                provenance={"format": node.get("format", "owl")},
            )


class HPOLoader(ConceptLoader):
    """Loader for the Human Phenotype Ontology."""

    ontology = "HPO"
    family = ConceptFamily.PHENOTYPE
    license_bucket = "open"

    def __init__(
        self, items: Sequence[HPONode], *, release_version: str = "2025-02-01"
    ) -> None:
        super().__init__(release_version=release_version)
        self._items = list(items)

    def load(self) -> Iterable[Concept]:
        for item in self._items:
            hp_id = str(item["id"])
            iri = f"http://purl.obolibrary.org/obo/{hp_id.replace(':', '_')}"
            label = str(item["label"])
            definition = item.get("definition")
            synonyms = [(syn, SynonymType.EXACT) for syn in (item.get("synonyms") or [])]
            attributes = {"diseases": [str(code) for code in (item.get("diseases") or [])]}
            yield self._build(
                iri=iri,
                label=label,
                preferred_term=str(item.get("preferred", label)),
                definition=str(definition) if definition else None,
                synonyms=synonyms,
                codes={"hpo": hp_id},
                attributes=attributes,
                provenance={"format": item.get("format", "obo")},
            )


class LOINCLoader(ConceptLoader):
    """Loader for the LOINC catalogue."""

    ontology = "LOINC"
    family = ConceptFamily.LAB
    license_bucket = "permissive"

    def __init__(
        self, rows: Sequence[LOINCRow], *, release_version: str = "2.77"
    ) -> None:
        super().__init__(release_version=release_version)
        self._rows = list(rows)

    def load(self) -> Iterable[Concept]:
        for row in self._rows:
            loinc = str(row["loinc_num"])
            iri = f"http://loinc.org/{loinc}"
            label = f"{row.get('component', '')} {row.get('property', '')}".strip()
            preferred = str(row.get("shortname", label or loinc))
            definition = row.get("long_common_name")
            synonyms = [
                (row.get("component", loinc), SynonymType.EXACT),
                (row.get("long_common_name", preferred), SynonymType.RELATED),
            ]
            attributes = {
                "system": row.get("system"),
                "scale": row.get("scale"),
                "method": row.get("method"),
                "ucum": row.get("ucum_unit"),
            }
            yield self._build(
                iri=iri,
                label=preferred,
                preferred_term=preferred,
                definition=str(definition) if definition else None,
                synonyms=synonyms,
                codes={"loinc": loinc},
                attributes=attributes,
                xrefs={"ucum": [str(row.get("ucum_unit"))] if row.get("ucum_unit") else []},
            )


class RxNormLoader(ConceptLoader):
    """Loader for RxNorm RRF exports."""

    ontology = "RxNorm"
    family = ConceptFamily.DRUG
    license_bucket = "open"

    def __init__(
        self, concepts: Sequence[RxNormConcept], *, release_version: str = "2025-01-01"
    ) -> None:
        super().__init__(release_version=release_version)
        self._concepts = list(concepts)

    def load(self) -> Iterable[Concept]:
        for concept in self._concepts:
            rxcui = str(concept["rxcui"])
            iri = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}"
            name = str(concept["name"])
            definition = concept.get("definition")
            synonyms = [(syn, SynonymType.RELATED) for syn in (concept.get("synonyms") or [])]
            attributes = {
                "tty": concept.get("tty"),
                "ingredients": [str(item) for item in (concept.get("ingredients") or [])],
            }
            yield self._build(
                iri=iri,
                label=name,
                preferred_term=name,
                definition=str(definition) if definition else None,
                synonyms=synonyms,
                codes={"rxcui": rxcui},
                attributes=attributes,
                xrefs={"snomed": [str(code) for code in (concept.get("snomed") or [])]},
            )


class UNIILoader(ConceptLoader):
    """Loader for FDA UNII registry."""

    ontology = "UNII"
    family = ConceptFamily.SUBSTANCE
    license_bucket = "open"

    def __init__(
        self, entries: Sequence[UNIIEntry], *, release_version: str = "2025-01-15"
    ) -> None:
        super().__init__(release_version=release_version)
        self._entries = list(entries)

    def load(self) -> Iterable[Concept]:
        for entry in self._entries:
            unii = str(entry["unii"])
            iri = f"https://fdasis.nlm.nih.gov/srs/unii/{unii}"
            name = str(entry["substance_name"])
            synonyms = [(syn, SynonymType.RELATED) for syn in (entry.get("synonyms") or [])]
            attributes = {"preferred_term": entry.get("preferred_term", name)}
            yield self._build(
                iri=iri,
                label=name,
                preferred_term=name,
                definition=None,
                synonyms=synonyms,
                codes={"unii": unii},
                attributes=attributes,
            )


class MedDRALoader(ConceptLoader):
    """Loader for MedDRA hierarchy (PT/LLT/SOC)."""

    ontology = "MedDRA"
    family = ConceptFamily.ADVERSE_EVENT
    license_bucket = "proprietary"

    def __init__(
        self, rows: Sequence[MedDRARow], *, release_version: str = "27.1"
    ) -> None:
        super().__init__(release_version=release_version)
        self._rows = list(rows)

    def load(self) -> Iterable[Concept]:
        for row in self._rows:
            code = str(row["code"])
            iri = f"https://meddra.org/meddra/{code}"
            label = str(row["pt"])
            level = str(row.get("level", "PT"))
            definition = row.get("definition")
            synonyms = [(syn, SynonymType.RELATED) for syn in (row.get("llt") or [])]
            attributes = {"soc": row.get("soc"), "level": level}
            parents = [
                f"https://meddra.org/meddra/{p}" for p in (row.get("parents") or [])
            ]
            yield self._build(
                iri=iri,
                label=label,
                preferred_term=label,
                definition=str(definition) if definition else None,
                synonyms=synonyms,
                codes={"meddra": code},
                parents=parents,
                attributes=attributes,
            )


class CTCAELoader(ConceptLoader):
    """Loader for CTCAE adverse event grading mapping to MedDRA."""

    ontology = "CTCAE"
    family = ConceptFamily.ADVERSE_EVENT
    license_bucket = "open"

    def __init__(
        self, grades: Sequence[CTCAERow], *, release_version: str = "5.0"
    ) -> None:
        super().__init__(release_version=release_version)
        self._grades = list(grades)

    def load(self) -> Iterable[Concept]:
        for grade in self._grades:
            meddra_code = str(grade["meddra_code"])
            iri = f"https://ctcae.nci.nih.gov/{meddra_code}"
            term = str(grade["term"])
            synonyms = [(term, SynonymType.EXACT)] + [
                (syn, SynonymType.RELATED) for syn in (grade.get("synonyms") or [])
            ]
            attributes = {
                "grade": grade.get("grade"),
                "description": grade.get("description"),
            }
            xrefs = {"meddra": [meddra_code]}
            yield self._build(
                iri=iri,
                label=term,
                preferred_term=term,
                definition=str(grade.get("description")) if grade.get("description") else None,
                synonyms=synonyms,
                codes={"ctcae": meddra_code},
                xrefs=xrefs,
                attributes=attributes,
            )


class AccessGUDIDLoader(ConceptLoader):
    """Loader for AccessGUDID device registry."""

    ontology = "GUDID"
    family = ConceptFamily.DEVICE
    license_bucket = "open"

    def __init__(
        self, devices: Sequence[GUDIDDevice], *, release_version: str = "2025-01-01"
    ) -> None:
        super().__init__(release_version=release_version)
        self._devices = list(devices)

    def load(self) -> Iterable[Concept]:
        for device in self._devices:
            di = str(device["di"])
            iri = f"https://accessgudid.nlm.nih.gov/devices/{di}"
            label = str(device["brand_name"])
            definition = device.get("model_number")
            synonyms = [(label, SynonymType.BRAND)] + [
                (syn, SynonymType.RELATED) for syn in (device.get("synonyms") or [])
            ]
            attributes = {
                "device_name": device.get("device_name"),
                "catalog_number": device.get("catalog_number"),
                "version": device.get("version"),
            }
            yield self._build(
                iri=iri,
                label=label,
                preferred_term=label,
                definition=str(definition) if definition else None,
                synonyms=synonyms,
                codes={"gudid": di},
                attributes=attributes,
            )


__all__ = [
    "AccessGUDIDLoader",
    "ConceptLoader",
    "CTCAELoader",
    "HPOLoader",
    "ICD11Loader",
    "LOINCLoader",
    "MONDOLoader",
    "MedDRALoader",
    "RxNormLoader",
    "SnomedCTLoader",
    "UNIILoader",
]
