"""Ontology loaders for the concept catalog (simplified for unit testing)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date
from typing import Iterable, Mapping, Sequence

from .models import Concept, ConceptFamily, Synonym, SynonymType
from .normalization import ConceptNormaliser


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
        self._normaliser = ConceptNormaliser()

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
        attributes: Mapping[str, object] | None = None,
        semantic_types: Sequence[str] | None = None,
        status: str = "active",
        provenance: Mapping[str, object] | None = None,
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
                **(provenance or {}),
            },
        )
        return self._normaliser.normalise(concept)


class SnomedCTLoader(ConceptLoader):
    """Simplified loader for SNOMED CT RF2 data."""

    ontology = "SNOMED"
    family = ConceptFamily.CONDITION
    license_bucket = "restricted"

    def __init__(
        self, records: Sequence[Mapping[str, object]], *, release_version: str = "2025-01-31"
    ) -> None:
        super().__init__(release_version=release_version)
        self._records = records

    def load(self) -> Iterable[Concept]:
        for record in self._records:
            concept_id = str(record["conceptId"])
            iri = f"http://snomed.info/id/{concept_id}"
            label = str(record["fsn"])
            preferred = str(record.get("preferred", label))
            definition = record.get("definition")
            synonyms = [(syn, SynonymType.EXACT) for syn in record.get("synonyms", [])]
            parents = [f"http://snomed.info/id/{pid}" for pid in record.get("parents", [])]
            ancestors = [f"http://snomed.info/id/{aid}" for aid in record.get("ancestors", [])]
            xrefs = {"icd10": [*map(str, record.get("icd10", []))]}
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
        self, entries: Sequence[Mapping[str, object]], *, release_version: str = "2025"
    ) -> None:
        super().__init__(release_version=release_version)
        self._entries = entries

    def load(self) -> Iterable[Concept]:
        for entry in self._entries:
            code = str(entry["code"])
            iri = f"https://id.who.int/icd/release/11/{code}"
            title = str(entry["title"])
            definition = entry.get("definition")
            parents = [
                f"https://id.who.int/icd/release/11/{parent}" for parent in entry.get("parents", [])
            ]
            synonyms = [(syn, SynonymType.RELATED) for syn in entry.get("synonyms", [])]
            xrefs = {"snomed": list(map(str, entry.get("snomed", [])))}
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
        self, nodes: Sequence[Mapping[str, object]], *, release_version: str = "2025-02"
    ) -> None:
        super().__init__(release_version=release_version)
        self._nodes = nodes

    def load(self) -> Iterable[Concept]:
        for node in self._nodes:
            identifier = str(node["id"])
            iri = f"http://purl.obolibrary.org/obo/{identifier.replace(':', '_')}"
            label = str(node["label"])
            definition = node.get("definition")
            synonyms = [(syn, SynonymType.RELATED) for syn in node.get("synonyms", [])]
            mappings = node.get("xrefs", {})
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
        self, items: Sequence[Mapping[str, object]], *, release_version: str = "2025-02-01"
    ) -> None:
        super().__init__(release_version=release_version)
        self._items = items

    def load(self) -> Iterable[Concept]:
        for item in self._items:
            hp_id = str(item["id"])
            iri = f"http://purl.obolibrary.org/obo/{hp_id.replace(':', '_')}"
            label = str(item["label"])
            definition = item.get("definition")
            synonyms = [(syn, SynonymType.EXACT) for syn in item.get("synonyms", [])]
            attributes = {"diseases": list(map(str, item.get("diseases", [])))}
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
        self, rows: Sequence[Mapping[str, object]], *, release_version: str = "2.77"
    ) -> None:
        super().__init__(release_version=release_version)
        self._rows = rows

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
        self, concepts: Sequence[Mapping[str, object]], *, release_version: str = "2025-01-01"
    ) -> None:
        super().__init__(release_version=release_version)
        self._concepts = concepts

    def load(self) -> Iterable[Concept]:
        for concept in self._concepts:
            rxcui = str(concept["rxcui"])
            iri = f"https://rxnav.nlm.nih.gov/REST/rxcui/{rxcui}"
            name = str(concept["name"])
            definition = concept.get("definition")
            synonyms = [(syn, SynonymType.RELATED) for syn in concept.get("synonyms", [])]
            attributes = {
                "tty": concept.get("tty"),
                "ingredients": list(map(str, concept.get("ingredients", []))),
            }
            yield self._build(
                iri=iri,
                label=name,
                preferred_term=name,
                definition=str(definition) if definition else None,
                synonyms=synonyms,
                codes={"rxcui": rxcui},
                attributes=attributes,
                xrefs={"snomed": list(map(str, concept.get("snomed", [])))},
            )


class UNIILoader(ConceptLoader):
    """Loader for FDA UNII registry."""

    ontology = "UNII"
    family = ConceptFamily.SUBSTANCE
    license_bucket = "open"

    def __init__(
        self, entries: Sequence[Mapping[str, object]], *, release_version: str = "2025-01-15"
    ) -> None:
        super().__init__(release_version=release_version)
        self._entries = entries

    def load(self) -> Iterable[Concept]:
        for entry in self._entries:
            unii = str(entry["unii"])
            iri = f"https://fdasis.nlm.nih.gov/srs/unii/{unii}"
            name = str(entry["substance_name"])
            synonyms = [(syn, SynonymType.RELATED) for syn in entry.get("synonyms", [])]
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
        self, rows: Sequence[Mapping[str, object]], *, release_version: str = "27.1"
    ) -> None:
        super().__init__(release_version=release_version)
        self._rows = rows

    def load(self) -> Iterable[Concept]:
        for row in self._rows:
            code = str(row["code"])
            iri = f"https://meddra.org/meddra/{code}"
            label = str(row["pt"])
            level = str(row.get("level", "PT"))
            definition = row.get("definition")
            synonyms = [(syn, SynonymType.RELATED) for syn in row.get("llt", [])]
            attributes = {"soc": row.get("soc"), "level": level}
            parents = [f"https://meddra.org/meddra/{p}" for p in row.get("parents", [])]
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
        self, grades: Sequence[Mapping[str, object]], *, release_version: str = "5.0"
    ) -> None:
        super().__init__(release_version=release_version)
        self._grades = grades

    def load(self) -> Iterable[Concept]:
        for grade in self._grades:
            meddra_code = str(grade["meddra_code"])
            iri = f"https://ctcae.nci.nih.gov/{meddra_code}"
            term = str(grade["term"])
            synonyms = [(term, SynonymType.EXACT)] + [
                (syn, SynonymType.RELATED) for syn in grade.get("synonyms", [])
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
        self, devices: Sequence[Mapping[str, object]], *, release_version: str = "2025-01-01"
    ) -> None:
        super().__init__(release_version=release_version)
        self._devices = devices

    def load(self) -> Iterable[Concept]:
        for device in self._devices:
            di = str(device["di"])
            iri = f"https://accessgudid.nlm.nih.gov/devices/{di}"
            label = str(device["brand_name"])
            definition = device.get("model_number")
            synonyms = [(label, SynonymType.BRAND)] + [
                (syn, SynonymType.RELATED) for syn in device.get("synonyms", [])
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
