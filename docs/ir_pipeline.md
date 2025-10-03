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

## Validation Rules

`IRValidator` enforces:

1. JSON Schema conformance for documents, blocks, and tables.
2. Presence of `doc_id` and `uri`.
3. Monotonic block offsets and span-map ordering.
4. Table span validity (`end >= start`).
5. Domain-specific guards (e.g., span maps must be non-empty when provided).

Validation failures raise `ValidationError` with contextual error messages; tests cover invalid spans, missing fields, and schema mismatches.

## Developer Workflow

1. Normalise text with `TextNormalizer` (UTF-8, NFC, whitespace collapse, dictionary de-hyphenation, language detection).
2. Build IR via the appropriate builder; attach provenance metadata to ensure traceability.
3. Persist through `IrStorage.write`, which content-addresses records and records ledger state transitions.
4. Validate using `IRValidator` before downstream ingestion into the knowledge graph.
