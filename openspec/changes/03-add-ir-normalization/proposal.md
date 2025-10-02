# Add Intermediate Representation (IR) Normalization

## Why

A uniform Intermediate Representation (IR) enables consistent downstream processing (chunking, embedding, extraction) regardless of source format (XML, JSON, HTML, PDF). The IR must preserve provenance (char offsets, page/bbox), normalize text canonically, and validate semantics per domain.

## What Changes

- Define JSON Schema for Document, Block, and Table IR objects
- Implement IR builders for each source adapter output
- Add canonicalization layer (UTF-8, Unicode NFC, whitespace collapse, de-hyphenation)
- Create span mapping system (char_to_page_bbox_map) for provenance
- Implement validation layer (schema + referential integrity + monotone offsets + domain rules)
- Add MinerU-specific provenance fields (mineru_run_id, mineru_version, mineru_artifacts)
- Create IR persistence layer (object store with content-addressable URIs)

## Impact

- **Affected specs**: NEW `ir-normalization` capability
- **Affected code**: NEW `/ir/schemas/`, `/ir/builder/`, `/ir/validator/`
- **Dependencies**: JSON Schema validator; object store; adapters (provides raw input)
- **Downstream**: Chunker, embeddings, extractors all consume IR
