# Intermediate Representation (IR) Guide

## Schema Overview

The IR is serialised as JSON objects conforming to the schemas under `src/Medical_KG/ir/schemas/`:

- `document.schema.json` – document-level metadata with `doc_id`, `source`, `uri`, canonicalised `text`, and a `span_map` describing transformations from `raw_text`.
- `block.schema.json` – block entries with `type` (`heading`, `paragraph`, `list_item`, etc.), `start`/`end` offsets, optional `section`, and `meta` for provenance.
- `table.schema.json` – table payloads with `caption`, column `headers`, `rows`, offsets, and `meta` (units, denominators, page numbers).

### Provenance & Span Maps

Every builder populates `DocumentIR.span_map` using `SpanMap.extend_from_offset_map()` to retain MinerU offsets or parser-provided character spans. Blocks and tables compute `start`/`end` during normalisation; the validator checks monotonicity and bounds.

## Builder Responsibilities

| Builder | Source | Key Features |
| --- | --- | --- |
| `ClinicalTrialsBuilder` | ClinicalTrials.gov v2 JSON | Creates blocks for title, status, eligibility, outcomes, plus a primary outcome table. |
| `PmcBuilder` | PMC JATS XML | Preserves IMRaD hierarchy, captions, span maps, and references. |
| `DailyMedBuilder` | DailyMed SPL XML | Emits LOINC-tagged blocks and ingredient tables. |
| `MinerUBuilder` | MinerU artifacts | Loads Markdown, structured blocks, tables, and offset maps. |
| `GuidelineBuilder` | HTML guidelines | Parses headings, paragraphs, list items, and HTML tables with a BeautifulSoup fallback using the standard library `HTMLParser`. |

To extend the system, create a new builder subclassing `IrBuilder`, call `super().build(...)`, then use `_add_blocks` / `document.add_table` to populate structured content.

### Typed Payload Integration

- `IrBuilder.build()` **requires** a typed `raw: AdapterDocumentPayload` argument. Calls that omit the payload raise `ValueError`, surfacing adapters that have not migrated to the typed contract.
- Literature payloads (PubMed, PMC, MedRxiv) emit title/abstract blocks, section hierarchies, and Mesh term provenance without JSON casting.
- Clinical trial payloads surface eligibility text, arm/outcome blocks, and populate the document provenance with the canonical NCT identifier.
- Guideline payloads (NICE, USPSTF) expose summary paragraphs and retain source URLs/licensing metadata in provenance.

#### Example: Building and validating a typed document

```python
from Medical_KG.ingestion.models import Document
from Medical_KG.ingestion.types import PubMedDocumentPayload
from Medical_KG.ir.builder import IrBuilder
from Medical_KG.ir.validator import IRValidator

payload: PubMedDocumentPayload = {
    "pmid": "12345",
    "title": "Example Title",
    "abstract": "Structured summary",
    "authors": ["Author One", "Author Two"],
    "mesh_terms": ["Term1"],
    "pub_types": ["Journal Article"],
}

document = Document(
    doc_id="pubmed:12345",
    source="pubmed",
    content=payload["abstract"],
    raw=payload,
)

ir = IrBuilder().build(
    doc_id=document.doc_id,
    source=document.source,
    uri="https://pubmed.ncbi.nlm.nih.gov/12345/",
    text=document.content,
    metadata=document.metadata,
    raw=document.raw,
)

IRValidator().validate_document(ir, raw=document.raw)
```

The resulting `DocumentIR.metadata` contains `payload_family`, `payload_type`, `identifier`, and other structured fields extracted directly from the typed payload, enabling downstream consumers to reason about source-specific metadata without casts.

## Validation Rules

`IRValidator` enforces:

1. JSON Schema conformance for documents, blocks, and tables.
2. Presence of `doc_id` and `uri`.
3. Monotonic block offsets and span-map ordering.
4. Table span validity (`end >= start`).
5. Domain-specific guards (e.g., span maps must be non-empty when provided).
6. Typed payload conformance—identifier, version, and summary fields extracted into `DocumentIR.metadata` must mirror the original adapter payload.

`IRValidator.validate_document(document, raw=payload)` now raises descriptive errors such as `"pubmed payload metadata field 'identifier' must equal '12345'"` when metadata and payload drift, guiding adapter authors toward fixing typed payload regressions.

Validation failures raise `ValidationError` with contextual error messages; tests cover invalid spans, missing fields, and schema mismatches.

## Developer Workflow

1. Normalise text with `TextNormalizer` (UTF-8, NFC, whitespace collapse, dictionary de-hyphenation, language detection).
2. Build IR via the appropriate builder; attach provenance metadata to ensure traceability.
3. Persist through `IrStorage.write`, which content-addresses records and records ledger state transitions.
4. Validate using `IRValidator` before downstream ingestion into the knowledge graph. Pass `raw=document.raw` so payload-aware checks (e.g., PubMed PMID/PMCID or clinical NCT ID provenance) run alongside schema validation.
