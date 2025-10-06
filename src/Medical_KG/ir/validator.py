from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping, cast

from Medical_KG.ingestion.types import (
    AdapterDocumentPayload,
    is_access_gudid_payload,
    is_cdc_socrata_payload,
    is_cdc_wonder_payload,
    is_clinical_document_payload,
    is_clinical_payload,
    is_dailymed_payload,
    is_guideline_payload,
    is_icd11_payload,
    is_knowledge_base_payload,
    is_literature_payload,
    is_loinc_payload,
    is_medrxiv_payload,
    is_mesh_payload,
    is_nice_guideline_payload,
    is_openfda_payload,
    is_openprescribing_payload,
    is_pmc_payload,
    is_pubmed_payload,
    is_rxnorm_payload,
    is_snomed_payload,
    is_terminology_payload,
    is_uspstf_payload,
    is_umls_payload,
)
from Medical_KG.ir.models import DocumentIR, ensure_monotonic_spans


class ValidationError(Exception):
    pass


class IRValidator:
    """Validate :class:`DocumentIR` instances using bundled JSON schemas."""

    def __init__(self, *, schema_dir: Path | None = None) -> None:
        base_dir = schema_dir or Path(__file__).resolve().parent / "schemas"
        self._schema_dir = base_dir
        self._schemas = {
            "document": self._load_schema(base_dir / "document.schema.json"),
            "block": self._load_schema(base_dir / "block.schema.json"),
            "table": self._load_schema(base_dir / "table.schema.json"),
        }
        language_pattern = self._schemas["document"]["properties"]["language"].get("pattern", "")
        self._language_pattern = re.compile(language_pattern) if language_pattern else None

    @property
    def schema_store(self) -> Mapping[str, Mapping[str, Any]]:
        """Expose loaded schemas for tests and tooling."""

        return dict(self._schemas)

    def _load_schema(self, path: Path) -> Mapping[str, Any]:
        result: Any = json.loads(path.read_text(encoding="utf-8"))
        return cast(Mapping[str, Any], result)

    def validate_document(
        self,
        document: DocumentIR,
        *,
        raw: AdapterDocumentPayload | None = None,
    ) -> None:
        payload = document.as_dict()
        if not document.doc_id:
            raise ValidationError("Document must have a doc_id")
        if not document.uri:
            raise ValidationError("Document must have a uri")

        self._validate_document_payload(payload)

        for block_payload in payload["blocks"]:
            self._validate_block_payload(block_payload)

        for table_payload in payload["tables"]:
            self._validate_table_payload(table_payload)

        try:
            ensure_monotonic_spans(document.blocks)
        except ValueError as exc:
            raise ValidationError(str(exc)) from exc
        self._validate_offsets(document)
        self._validate_span_map(payload["span_map"])
        self._validate_metadata(document, raw)
        if raw is not None:
            self._validate_payload(document, raw)

    def _validate_document_payload(self, payload: Mapping[str, Any]) -> None:
        schema = self._schemas["document"]
        required = schema.get("required", [])
        missing = [field for field in required if field not in payload]
        if missing:
            raise ValidationError(f"Document missing required fields: {', '.join(missing)}")

        for field in ("doc_id", "source", "uri", "language", "text", "raw_text"):
            value = payload.get(field)
            if not isinstance(value, str):
                raise ValidationError(f"Document field '{field}' must be a string")
            if field in {"doc_id", "source", "uri"} and not value.strip():
                raise ValidationError(f"Document field '{field}' cannot be empty")

        if self._language_pattern and not self._language_pattern.fullmatch(payload["language"]):
            raise ValidationError("Document language must be a two-letter code")

        if not isinstance(payload.get("blocks"), list):
            raise ValidationError("Document blocks must be an array")
        if not isinstance(payload.get("tables"), list):
            raise ValidationError("Document tables must be an array")
        if not isinstance(payload.get("span_map"), list):
            raise ValidationError("Document span_map must be an array")

        provenance = payload.get("provenance", {})
        if provenance is not None and not isinstance(provenance, dict):
            raise ValidationError("Document provenance must be an object")

        metadata = payload.get("metadata", {})
        if metadata is not None and not isinstance(metadata, dict):
            raise ValidationError("Document metadata must be an object")

        allowed_keys = set(schema.get("properties", {}).keys()) | {"created_at"}
        extras = set(payload.keys()) - allowed_keys
        if extras:
            raise ValidationError(
                f"Document contains unsupported fields: {', '.join(sorted(extras))}"
            )

    def _validate_block_payload(self, block: Mapping[str, Any]) -> None:
        schema = self._schemas["block"]
        required = schema.get("required", [])
        missing = [field for field in required if field not in block]
        if missing:
            raise ValidationError(f"Block missing required fields: {', '.join(missing)}")

        allowed_keys = set(schema.get("properties", {}).keys())
        extras = set(block.keys()) - allowed_keys
        if extras:
            raise ValidationError(f"Block contains unsupported fields: {', '.join(sorted(extras))}")

        if not isinstance(block["type"], str) or not block["type"]:
            raise ValidationError("Block type must be a non-empty string")
        if not isinstance(block["text"], str):
            raise ValidationError("Block text must be a string")
        for field in ("start", "end"):
            value = block[field]
            if not isinstance(value, int) or value < 0:
                raise ValidationError(f"Block {field} must be a non-negative integer")

        section = block.get("section")
        if section is not None and not isinstance(section, str):
            raise ValidationError("Block section must be a string or None")

        meta = block.get("meta", {})
        if not isinstance(meta, dict):
            raise ValidationError("Block meta must be an object")

    def _validate_table_payload(self, table: Mapping[str, Any]) -> None:
        schema = self._schemas["table"]
        required = schema.get("required", [])
        missing = [field for field in required if field not in table]
        if missing:
            raise ValidationError(f"Table missing required fields: {', '.join(missing)}")

        allowed_keys = set(schema.get("properties", {}).keys())
        extras = set(table.keys()) - allowed_keys
        if extras:
            raise ValidationError(f"Table contains unsupported fields: {', '.join(sorted(extras))}")

        if not isinstance(table["caption"], str):
            raise ValidationError("Table caption must be a string")
        if not isinstance(table.get("headers"), list):
            raise ValidationError("Table headers must be an array")
        if not all(isinstance(header, str) for header in table["headers"]):
            raise ValidationError("Table headers must be strings")
        if not isinstance(table.get("rows"), list):
            raise ValidationError("Table rows must be an array")
        for row in table["rows"]:
            if not isinstance(row, list) or not all(isinstance(cell, str) for cell in row):
                raise ValidationError("Table rows must be arrays of strings")

        for field in ("start", "end"):
            value = table[field]
            if not isinstance(value, int) or value < 0:
                raise ValidationError(f"Table {field} must be a non-negative integer")
        if table["end"] < table["start"]:
            raise ValidationError("Table span invalid")

        meta = table.get("meta", {})
        if not isinstance(meta, dict):
            raise ValidationError("Table meta must be an object")

    def _validate_offsets(self, document: DocumentIR) -> None:
        text_length = len(document.text)
        for block in document.blocks:
            if block.end > text_length:
                raise ValidationError("Block span exceeds document length")
            if block.section is not None and not isinstance(block.section, str):
                raise ValidationError("Block section must be a string or None")

    def _validate_span_map(self, span_map: list[Mapping[str, Any]]) -> None:
        previous_end = 0
        for entry in span_map:
            canonical_start = entry["canonical_start"]
            canonical_end = entry["canonical_end"]
            if canonical_start > canonical_end:
                raise ValidationError("Span map canonical offsets invalid")
            if canonical_start < previous_end:
                raise ValidationError("Span map must be monotonic")
            if "page" in entry and entry["page"] is not None and entry["page"] < 1:
                raise ValidationError("Span map page numbers must be >= 1")
            previous_end = canonical_end

    def _validate_metadata(
        self, document: DocumentIR, raw: AdapterDocumentPayload | None
    ) -> None:
        metadata = document.metadata
        if not isinstance(metadata, Mapping):
            raise ValidationError("Document metadata must be a mapping")
        if raw is None:
            return
        family = metadata.get("payload_family")
        if not isinstance(family, str) or not family:
            raise ValidationError("Document metadata missing payload_family for typed payload")
        payload_type = metadata.get("payload_type")
        if not isinstance(payload_type, str) or not payload_type:
            raise ValidationError("Document metadata missing payload_type for typed payload")

        if is_literature_payload(raw):
            if is_pubmed_payload(raw):
                self._require_identifier(metadata, raw["pmid"], "PubMed")
                self._require_title(metadata, raw.get("title", ""), "PubMed")
            elif is_pmc_payload(raw):
                self._require_identifier(metadata, raw["pmcid"], "PMC")
                self._require_title(metadata, raw.get("title", ""), "PMC")
            elif is_medrxiv_payload(raw):
                self._require_identifier(metadata, raw["doi"], "MedRxiv")
                self._require_title(metadata, raw.get("title", ""), "MedRxiv")
        elif is_clinical_payload(raw):
            if is_clinical_document_payload(raw):
                self._require_identifier(metadata, raw["nct_id"], "ClinicalTrials")
                self._require_title(metadata, raw.get("title", ""), "ClinicalTrials")
                self._require_version(metadata, raw.get("version", ""), "ClinicalTrials")
            elif is_openfda_payload(raw):
                self._require_identifier(metadata, raw["identifier"], "OpenFDA")
                self._require_version(metadata, raw["version"], "OpenFDA")
            elif is_dailymed_payload(raw):
                self._require_identifier(metadata, raw["setid"], "DailyMed")
                self._require_title(metadata, raw.get("title", ""), "DailyMed")
                self._require_version(metadata, raw.get("version", ""), "DailyMed")
            elif is_rxnorm_payload(raw):
                self._require_identifier(metadata, raw["rxcui"], "RxNorm")
            elif is_access_gudid_payload(raw):
                self._require_identifier(metadata, raw["udi_di"], "AccessGUDID")
        elif is_guideline_payload(raw):
            if is_nice_guideline_payload(raw):
                self._require_identifier(metadata, raw["uid"], "NICE")
                self._require_title(metadata, raw.get("title", ""), "NICE")
            elif is_uspstf_payload(raw):
                identifier = raw.get("id", "") or raw.get("title", "")
                self._require_identifier(metadata, identifier, "USPSTF")
                self._require_title(metadata, raw.get("title", ""), "USPSTF")
        elif is_knowledge_base_payload(raw):
            if is_cdc_socrata_payload(raw):
                self._require_identifier(metadata, raw["identifier"], "CDC Socrata")
            elif is_openprescribing_payload(raw):
                self._require_identifier(metadata, raw["identifier"], "OpenPrescribing")
            elif is_cdc_wonder_payload(raw):
                if "row_count" not in metadata:
                    raise ValidationError("CDC Wonder metadata must include row_count")
        elif is_terminology_payload(raw):
            if is_mesh_payload(raw):
                self._require_identifier(metadata, raw.get("descriptor_id", "") or raw["name"], "MeSH")
                self._require_title(metadata, raw["name"], "MeSH")
            elif is_umls_payload(raw):
                self._require_identifier(metadata, raw.get("cui", ""), "UMLS", optional=True)
            elif is_loinc_payload(raw):
                self._require_identifier(metadata, raw.get("code", ""), "LOINC", optional=True)
            elif is_icd11_payload(raw):
                self._require_identifier(metadata, raw.get("code", ""), "ICD-11", optional=True)
            elif is_snomed_payload(raw):
                self._require_identifier(metadata, raw.get("code", ""), "SNOMED", optional=True)

    def _require_identifier(
        self,
        metadata: Mapping[str, Any],
        expected: str | None,
        context: str,
        *,
        optional: bool = False,
    ) -> None:
        if not expected and optional:
            return
        actual = metadata.get("identifier")
        if not actual:
            raise ValidationError(f"{context} metadata must include identifier")
        if expected and actual != expected:
            raise ValidationError(f"{context} metadata identifier mismatch")

    def _require_title(
        self, metadata: Mapping[str, Any], expected: str, context: str
    ) -> None:
        if not expected:
            return
        title = metadata.get("title")
        if not title:
            raise ValidationError(f"{context} metadata must include title")

    def _require_version(
        self, metadata: Mapping[str, Any], expected: str, context: str
    ) -> None:
        if not expected:
            return
        version = metadata.get("version")
        if not version:
            raise ValidationError(f"{context} metadata must include version")

    def _validate_payload(
        self,
        document: DocumentIR,
        raw: AdapterDocumentPayload,
    ) -> None:
        provenance = document.provenance
        if is_clinical_document_payload(raw):
            if provenance.get("nct_id") != raw["nct_id"]:
                raise ValidationError("Clinical IR documents must include NCT ID provenance")
        if is_pubmed_payload(raw):
            pubmed_info = provenance.get("pubmed")
            pmid_source: Any | None = None
            if isinstance(pubmed_info, Mapping):
                pmid_source = pubmed_info.get("pmid")
            if pmid_source is None:
                pmid_source = provenance.get("pmid")
            if pmid_source != raw["pmid"]:
                raise ValidationError("PubMed IR documents must include PMID provenance")
            expected_pmcid = raw.get("pmcid")
            if expected_pmcid:
                pmcid_source: Any | None = None
                if isinstance(pubmed_info, Mapping):
                    pmcid_source = pubmed_info.get("pmcid")
                if pmcid_source is None:
                    pmcid_source = provenance.get("pmcid")
                if pmcid_source != expected_pmcid:
                    raise ValidationError(
                        "PubMed IR documents must include PMCID provenance when available"
                    )
        if is_pmc_payload(raw):
            pmcid_source = provenance.get("pmcid")
            if pmcid_source != raw["pmcid"]:
                pubmed_info = provenance.get("pubmed")
                if not (
                    isinstance(pubmed_info, Mapping) and pubmed_info.get("pmcid") == raw["pmcid"]
                ):
                    raise ValidationError("PMC IR documents must include PMCID provenance")
