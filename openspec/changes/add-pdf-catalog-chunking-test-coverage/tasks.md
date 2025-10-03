# Implementation Tasks

## 1. Test Fixtures & Mocks

- [ ] 1.1 Create sample PDF files: simple text, tables, equations, multi-column, scanned (OCR)
- [ ] 1.2 Create sample MinerU JSON outputs for each PDF type
- [ ] 1.3 Create sample concept catalog files (UMLS MRCONSO.RRF, RxNorm, SNOMED)
- [ ] 1.4 Create sample license policies for catalog loaders
- [x] 1.5 Mock GPU availability for MinerU service

## 2. PDF Service Tests

- [x] 2.1 Test PDF → IR conversion: verify blocks, paragraphs, tables, metadata
- [ ] 2.2 Test table extraction: verify cell text, row/column spans, and captions
- [ ] 2.3 Test OCR handling: verify scanned PDFs are processed correctly
- [x] 2.4 Test metadata preservation: verify title, authors, DOI, publication date
- [ ] 2.5 Test multi-column layout: verify correct reading order
- [x] 2.6 Test error handling: verify corrupted PDFs are rejected with clear errors

## 3. PDF Post-Processing Tests

- [x] 3.1 Test header/footer removal: verify repeated text is stripped
- [ ] 3.2 Test equation normalization: verify LaTeX equations are formatted consistently
- [ ] 3.3 Test reference extraction: verify bibliography is parsed into citations
- [ ] 3.4 Test figure caption extraction: verify captions are linked to figures
- [x] 3.5 Test hyphenation repair: verify split words are rejoined

## 4. PDF QA Validation Tests

- [x] 4.1 Test structure checks: verify required sections (title, abstract, body) are present
- [x] 4.2 Test missing section detection: verify warnings for missing methods/results
- [x] 4.3 Test quality scoring: verify low-quality PDFs (OCR errors, garbled text) are flagged
- [ ] 4.4 Test page count validation: verify minimum/maximum page limits
- [ ] 4.5 Test language detection: verify non-English PDFs are handled appropriately

## 5. Concept Catalog Loader Tests

- [ ] 5.1 Test UMLS loader: verify parsing MRCONSO.RRF, deduplication by CUI
- [ ] 5.2 Test RxNorm loader: verify drug concept extraction, ingredient parsing
- [ ] 5.3 Test SNOMED loader: verify concept hierarchy, relationships, descriptions
- [ ] 5.4 Test crosswalk creation: verify linking concepts across vocabularies
- [ ] 5.5 Test incremental loading: verify updating existing catalog without full reload
- [ ] 5.6 Test error handling: verify malformed files are rejected with clear errors

## 6. License Policy Tests

- [x] 6.1 Test free tier: verify only public domain concepts are loaded
- [ ] 6.2 Test pro tier: verify licensed vocabularies (e.g., SNOMED) are included
- [x] 6.3 Test loader skipping: verify loaders are skipped when license is insufficient
- [ ] 6.4 Test policy updates: verify catalog is rebuilt when license tier changes

## 7. Concept Graph Writer Tests

- [ ] 7.1 Test concept node creation: verify CUI, name, vocabulary, semantic type
- [ ] 7.2 Test crosswalk relationship creation: verify links between equivalent concepts
- [ ] 7.3 Test hierarchy relationships: verify IS_A, PART_OF relationships
- [ ] 7.4 Test batch operations: verify efficient bulk loading
- [ ] 7.5 Test constraint enforcement: verify duplicate CUIs are rejected

## 8. Concept Index Manager Tests

- [ ] 8.1 Test OpenSearch indexing: verify concepts are indexed with text, embeddings, metadata
- [ ] 8.2 Test search functionality: verify fuzzy search, exact match, and synonym expansion
- [ ] 8.3 Test filtering: verify filtering by vocabulary, semantic type
- [ ] 8.4 Test ranking: verify search results are ranked by relevance
- [ ] 8.5 Test index updates: verify incremental updates without full reindex

## 9. Chunking Pipeline Tests

- [x] 9.1 Test semantic chunking: verify chunks respect sentence/paragraph boundaries
- [ ] 9.2 Test configurable profiles: verify small/medium/large chunk sizes
- [ ] 9.3 Test chunk ID stability: verify deterministic IDs based on content hash
- [x] 9.4 Test metadata propagation: verify document ID, section, page number in chunks
- [x] 9.5 Test multi-granularity indexing: verify parent-child chunk relationships
- [ ] 9.6 Test error handling: verify empty documents or oversized chunks are handled

## 10. Neighbor Merging Tests

- [ ] 10.1 Test similarity threshold: verify chunks below threshold are not merged
- [ ] 10.2 Test merge constraints: verify max chunk size is respected
- [ ] 10.3 Test merge order: verify merging proceeds left-to-right
- [ ] 10.4 Test edge cases: verify single-sentence chunks, very similar adjacent chunks

## 11. Guardrails Tests

- [x] 11.1 Test list item grouping: verify numbered/bulleted lists stay together
- [ ] 11.2 Test table preservation: verify tables are not split across chunks
- [ ] 11.3 Test code block handling: verify code blocks are preserved intact
- [ ] 11.4 Test section boundaries: verify chunks respect section headers
- [ ] 11.5 Test quote preservation: verify block quotes are not split

## 12. Coverage & Validation

- [ ] 12.1 Run `pytest tests/pdf/ tests/catalog/ tests/chunking/ --cov=src/Medical_KG/pdf --cov=src/Medical_KG/catalog --cov=src/Medical_KG/chunking --cov-report=term-missing`
- [ ] 12.2 Verify 100% coverage for all PDF, catalog, and chunking modules
- [x] 12.3 Ensure no GPU or external service calls in test suite (mock all dependencies)
- [ ] 12.4 Document PDF, catalog, and chunking test patterns in respective README files
