# Implementation Tasks

## 1. Schema Definition

- [x] 1.1 Define Document schema (JSON Schema draft 2020-12)
- [x] 1.2 Define Block schema (paragraph, heading, list_item, clause, caption, eligibility, definition)
- [x] 1.3 Define Table schema (rows[], html, meta with units/arms/denominators)
- [x] 1.4 Add provenance fields (parser, mineru_run_id, mineru_version, mineru_artifacts)
- [x] 1.5 Create span mapping schema (char_to_page_bbox_map)

## 2. Canonicalization

- [x] 2.1 Implement UTF-8 + Unicode NFC normalization
- [x] 2.2 Implement whitespace collapse (preserve single spaces, remove leading/trailing)
- [x] 2.3 Implement dictionary-guarded de-hyphenation
- [x] 2.4 Preserve raw_text alongside canonical text
- [x] 2.5 Add language detection (fasttext/CLD → ISO 639-1 code)

## 3. IR Builders per Source

- [x] 3.1 ClinicalTrials.gov → IR (structured blocks by section; tables for AEs/outcomes/flow)
- [x] 3.2 PMC JATS → IR (IMRaD sections; tables with captions; figure captions; references)
- [x] 3.3 DailyMed SPL → IR (LOINC-coded section blocks; ingredient tables)
- [x] 3.4 MinerU artifacts → IR (markdown + blocks + tables + offset map)
- [x] 3.5 HTML guidelines → IR (heading hierarchy; recommendation blocks; evidence tables)

## 4. Span Mapping & Provenance

- [x] 4.1 Generate char_to_page_bbox_map for PDFs (from MinerU offset_map.json)
- [x] 4.2 Compute start_char/end_char for all Blocks and Tables
- [x] 4.3 Validate monotone offsets (start_char ≤ end_char; non-overlapping or parent/child only)
- [x] 4.4 Store bbox [x0, y0, x1, y1] when available

## 5. Validation Layer

- [x] 5.1 Implement JSON Schema validation (ajv or jsonschema)
- [x] 5.2 Implement referential integrity (Block/Table doc_id must match Document doc_id)
- [x] 5.3 Implement offset monotonicity check
- [x] 5.4 Implement domain-specific rules (e.g., SPL must have loinc_section for key blocks)
- [x] 5.5 Emit ValidationReport with errors/warnings

## 6. Persistence

- [x] 6.1 Implement write to object store (JSONL; one line per Document/Block/Table)
- [x] 6.2 Generate content-addressable URI (s3://bucket/ir/{source}/{doc_id_prefix}/{doc_id}.jsonl)
- [x] 6.3 Add idempotency (if URI exists with same content hash, skip write)
- [x] 6.4 Update ledger with ir_uri after successful write

## 7. Testing

- [x] 7.1 Unit tests for canonicalization (UTF-8, NFC, de-hyphenation)
- [x] 7.2 Unit tests for each IR builder (sample inputs → expected IR)
- [x] 7.3 Integration tests (adapter → IR builder → validator → persistence)
- [x] 7.4 Test span map integrity (all quotes resolvable to original text)
- [x] 7.5 Test validation failures (missing fields, invalid offsets, broken refs)

## 8. Documentation

- [x] 8.1 Document IR schema with examples per source type
- [x] 8.2 Create IR builder developer guide
- [x] 8.3 Document validation rules and common failure modes
