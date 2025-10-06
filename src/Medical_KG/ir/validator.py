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
    is_dailymed_payload,
    is_icd11_payload,
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
    is_umls_payload,
    is_uspstf_payload,
    is_who_gho_payload,
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
        raw: AdapterDocumentPayload,
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

    def _validate_metadata(
        self,
        document: DocumentIR,
        raw: AdapterDocumentPayload,
    ) -> None:
        metadata = document.metadata
        if not isinstance(metadata, Mapping):
            raise ValidationError("Document metadata must be a mapping")
        expected_family = self._expected_payload_family(raw)
        observed_family = metadata.get("payload_family")
        if expected_family != "unknown" and observed_family != expected_family:
            raise ValidationError(
                f"{self._payload_label(raw)} metadata must record payload_family='{expected_family}'"
            )
        expected_type = self._expected_payload_type(raw)
        observed_type = metadata.get("payload_type")
        if expected_type != "unknown" and observed_type != expected_type:
            raise ValidationError(
                f"{self._payload_label(raw)} metadata must record payload_type='{expected_type}'"
            )
        if is_pubmed_payload(raw):
            self._assert_metadata_value(metadata, "identifier", raw["pmid"], raw)
            self._assert_metadata_value(metadata, "title", raw["title"], raw)
            abstract = raw.get("abstract", "")
            if abstract:
                self._assert_metadata_value(metadata, "summary", abstract, raw)
        elif is_pmc_payload(raw):
            self._assert_metadata_value(metadata, "identifier", raw["pmcid"], raw)
            self._assert_metadata_value(metadata, "title", raw["title"], raw)
            if raw.get("abstract"):
                self._assert_metadata_value(metadata, "summary", raw["abstract"], raw)
        elif is_medrxiv_payload(raw):
            self._assert_metadata_value(metadata, "identifier", raw["doi"], raw)
            self._assert_metadata_value(metadata, "title", raw["title"], raw)
            if raw.get("abstract"):
                self._assert_metadata_value(metadata, "summary", raw["abstract"], raw)
            if raw.get("date"):
                self._assert_metadata_value(metadata, "version", raw["date"], raw)
        if is_clinical_document_payload(raw):
            self._assert_metadata_value(metadata, "identifier", raw["nct_id"], raw)
            self._assert_metadata_value(metadata, "title", raw["title"], raw)
            if raw.get("version"):
                self._assert_metadata_value(metadata, "version", raw["version"], raw)
        if is_openfda_payload(raw):
            self._assert_metadata_value(metadata, "identifier", raw["identifier"], raw)
            self._assert_metadata_value(metadata, "version", raw["version"], raw)
            self._assert_metadata_value(metadata, "record", raw["record"], raw)
        if is_dailymed_payload(raw):
            self._assert_metadata_value(metadata, "identifier", raw["setid"], raw)
            self._assert_metadata_value(metadata, "title", raw["title"], raw)
            if raw.get("version"):
                self._assert_metadata_value(metadata, "version", raw["version"], raw)
        if is_rxnorm_payload(raw):
            self._assert_metadata_value(metadata, "identifier", raw["rxcui"], raw)
            if raw.get("name"):
                self._assert_metadata_value(metadata, "title", raw["name"], raw)
        if is_access_gudid_payload(raw):
            self._assert_metadata_value(metadata, "identifier", raw["udi_di"], raw)
            if raw.get("brand"):
                self._assert_metadata_value(metadata, "title", raw["brand"], raw)
        if is_nice_guideline_payload(raw):
            self._assert_metadata_value(metadata, "identifier", raw["uid"], raw)
            self._assert_metadata_value(metadata, "title", raw["title"], raw)
            if raw.get("summary"):
                self._assert_metadata_value(metadata, "summary", raw["summary"], raw)
        if is_uspstf_payload(raw):
            self._assert_metadata_value(metadata, "title", raw["title"], raw)
            if raw.get("id"):
                self._assert_metadata_value(metadata, "identifier", raw["id"], raw)
            if raw.get("status"):
                self._assert_metadata_value(metadata, "status", raw["status"], raw)
        if is_mesh_payload(raw):
            if raw.get("descriptor_id"):
                self._assert_metadata_value(metadata, "identifier", raw["descriptor_id"], raw)
            self._assert_metadata_value(metadata, "title", raw["name"], raw)
        if is_umls_payload(raw):
            if raw.get("cui"):
                self._assert_metadata_value(metadata, "identifier", raw["cui"], raw)
            if raw.get("name"):
                self._assert_metadata_value(metadata, "title", raw["name"], raw)
        if is_loinc_payload(raw):
            if raw.get("code"):
                self._assert_metadata_value(metadata, "identifier", raw["code"], raw)
            if raw.get("display"):
                self._assert_metadata_value(metadata, "title", raw["display"], raw)
        if is_icd11_payload(raw):
            if raw.get("code"):
                self._assert_metadata_value(metadata, "identifier", raw["code"], raw)
            if raw.get("title"):
                self._assert_metadata_value(metadata, "title", raw["title"], raw)
        if is_snomed_payload(raw):
            if raw.get("code"):
                self._assert_metadata_value(metadata, "identifier", raw["code"], raw)
            if raw.get("display"):
                self._assert_metadata_value(metadata, "title", raw["display"], raw)
        if is_cdc_socrata_payload(raw):
            self._assert_metadata_value(metadata, "identifier", raw["identifier"], raw)
            self._assert_metadata_value(metadata, "record", raw["record"], raw)
        if is_cdc_wonder_payload(raw):
            if metadata.get("record_rows") != raw["rows"]:
                raise ValidationError(
                    f"{self._payload_label(raw)} metadata must expose record_rows matching CDC Wonder rows"
                )
        if is_who_gho_payload(raw):
            if raw.get("indicator"):
                self._assert_metadata_value(metadata, "indicator", raw["indicator"], raw)
            self._assert_metadata_value(metadata, "value", raw.get("value"), raw)
            if raw.get("country"):
                self._assert_metadata_value(metadata, "country", raw["country"], raw)
            if raw.get("year"):
                self._assert_metadata_value(metadata, "version", raw["year"], raw)
        if is_openprescribing_payload(raw):
            self._assert_metadata_value(metadata, "identifier", raw["identifier"], raw)
            self._assert_metadata_value(metadata, "record", raw["record"], raw)

    def _assert_metadata_value(
        self,
        metadata: Mapping[str, Any],
        key: str,
        expected: Any,
        raw: AdapterDocumentPayload,
    ) -> None:
        if expected in (None, "", [], {}):
            return
        value = metadata.get(key)
        if value != expected:
            raise ValidationError(
                f"{self._payload_label(raw)} metadata field '{key}' must equal {expected!r}"
            )

    def _expected_payload_family(self, raw: AdapterDocumentPayload) -> str:
        if is_pubmed_payload(raw) or is_pmc_payload(raw) or is_medrxiv_payload(raw):
            return "literature"
        if (
            is_clinical_document_payload(raw)
            or is_openfda_payload(raw)
            or is_dailymed_payload(raw)
            or is_rxnorm_payload(raw)
            or is_access_gudid_payload(raw)
        ):
            return "clinical"
        if is_nice_guideline_payload(raw) or is_uspstf_payload(raw):
            return "guideline"
        if (
            is_mesh_payload(raw)
            or is_umls_payload(raw)
            or is_loinc_payload(raw)
            or is_icd11_payload(raw)
            or is_snomed_payload(raw)
        ):
            return "terminology"
        if (
            is_cdc_socrata_payload(raw)
            or is_cdc_wonder_payload(raw)
            or is_who_gho_payload(raw)
            or is_openprescribing_payload(raw)
        ):
            return "knowledge_base"
        return "unknown"

    def _expected_payload_type(self, raw: AdapterDocumentPayload) -> str:
        if is_pubmed_payload(raw):
            return "pubmed"
        if is_pmc_payload(raw):
            return "pmc"
        if is_medrxiv_payload(raw):
            return "medrxiv"
        if is_clinical_document_payload(raw):
            return "clinical_document"
        if is_openfda_payload(raw):
            return "openfda"
        if is_dailymed_payload(raw):
            return "dailymed"
        if is_rxnorm_payload(raw):
            return "rxnorm"
        if is_access_gudid_payload(raw):
            return "access_gudid"
        if is_nice_guideline_payload(raw):
            return "nice_guideline"
        if is_uspstf_payload(raw):
            return "uspstf_guideline"
        if is_mesh_payload(raw):
            return "mesh"
        if is_umls_payload(raw):
            return "umls"
        if is_loinc_payload(raw):
            return "loinc"
        if is_icd11_payload(raw):
            return "icd11"
        if is_snomed_payload(raw):
            return "snomed"
        if is_cdc_socrata_payload(raw):
            return "cdc_socrata"
        if is_cdc_wonder_payload(raw):
            return "cdc_wonder"
        if is_who_gho_payload(raw):
            return "who_gho"
        if is_openprescribing_payload(raw):
            return "openprescribing"
        return "unknown"

    def _payload_label(self, raw: AdapterDocumentPayload) -> str:
        payload_type = self._expected_payload_type(raw)
        if payload_type != "unknown":
            return f"{payload_type} payload"
        family = self._expected_payload_family(raw)
        if family != "unknown":
            return f"{family} payload"
        return "adapter payload"
