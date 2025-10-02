# Implementation Tasks

## 1. Schema Definition

- [ ] 1.1 Define Document schema (JSON Schema draft 2020-12)
- [ ] 1.2 Define Block schema (paragraph, heading, list_item, clause, caption, eligibility, definition)
- [ ] 1.3 Define Table schema (rows[], html, meta with units/arms/denominators)
- [ ] 1.4 Add provenance fields (parser, mineru_run_id, mineru_version, mineru_artifacts)
- [ ] 1.5 Create span mapping schema (char_to_page_bbox_map)

## 2. Canonicalization

- [ ] 2.1 Implement UTF-8 + Unicode NFC normalization
- [ ] 2.2 Implement whitespace collapse (preserve single spaces, remove leading/trailing)
- [ ] 2.3 Implement dictionary-guarded de-hyphenation
- [ ] 2.4 Preserve raw_text alongside canonical text
- [ ] 2.5 Add language detection (fasttext/CLD → ISO 639-1 code)

## 3. IR Builders per Source

- [ ] 3.1 ClinicalTrials.gov → IR (structured blocks by section; tables for AEs/outcomes/flow)
- [ ] 3.2 PMC JATS → IR (IMRaD sections; tables with captions; figure captions; references)
- [ ] 3.3 DailyMed SPL → IR (LOINC-coded section blocks; ingredient tables)
- [ ] 3.4 MinerU artifacts → IR (markdown + blocks + tables + offset map)
- [ ] 3.5 HTML guidelines → IR (heading hierarchy; recommendation blocks; evidence tables)

## 4. Span Mapping & Provenance

- [ ] 4.1 Generate char_to_page_bbox_map for PDFs (from MinerU offset_map.json)
- [ ] 4.2 Compute start_char/end_char for all Blocks and Tables
- [ ] 4.3 Validate monotone offsets (start_char ≤ end_char; non-overlapping or parent/child only)
- [ ] 4.4 Store bbox [x0, y0, x1, y1] when available

## 5. Validation Layer

- [ ] 5.1 Implement JSON Schema validation (ajv or jsonschema)
- [ ] 5.2 Implement referential integrity (Block/Table doc_id must match Document doc_id)
- [ ] 5.3 Implement offset monotonicity check
- [ ] 5.4 Implement domain-specific rules (e.g., SPL must have loinc_section for key blocks)
- [ ] 5.5 Emit ValidationReport with errors/warnings

## 6. Persistence

- [ ] 6.1 Implement write to object store (JSONL; one line per Document/Block/Table)
- [ ] 6.2 Generate content-addressable URI (s3://bucket/ir/{source}/{doc_id_prefix}/{doc_id}.jsonl)
- [ ] 6.3 Add idempotency (if URI exists with same content hash, skip write)
- [ ] 6.4 Update ledger with ir_uri after successful write

## 7. Testing

- [ ] 7.1 Unit tests for canonicalization (UTF-8, NFC, de-hyphenation)
- [ ] 7.2 Unit tests for each IR builder (sample inputs → expected IR)
- [ ] 7.3 Integration tests (adapter → IR builder → validator → persistence)
- [ ] 7.4 Test span map integrity (all quotes resolvable to original text)
- [ ] 7.5 Test validation failures (missing fields, invalid offsets, broken refs)

## 8. Documentation

- [ ] 8.1 Document IR schema with examples per source type
- [ ] 8.2 Create IR builder developer guide
- [ ] 8.3 Document validation rules and common failure modes
