## Why

PDF processing, concept catalog, and chunking modules have incomplete test coverage. PDF/MinerU pipeline, post-processing, QA validation are untested. Concept catalog loaders (UMLS, RxNorm, SNOMED), license filtering, and Neo4j/OpenSearch indexing are partially tested. Chunking pipeline, neighbor merging, and guardrails have basic tests but miss error cases. These modules handle raw document ingestion and semantic chunking—failures here corrupt downstream data.

## What Changes

- Add unit tests for `PDFService` and `MinerUService`: verify PDF → IR conversion, table extraction, OCR handling, and metadata preservation.
- Test PDF post-processing: verify header/footer removal, equation normalization, and reference extraction.
- Test PDF QA validation: verify document structure checks, missing section detection, and quality scoring.
- Test concept catalog loaders: verify loading from UMLS, RxNorm, SNOMED files, deduplication, and crosswalk creation.
- Test license policy filtering: verify loader skipping based on license tiers.
- Test concept graph writer: verify Neo4j node/relationship creation for concepts and crosswalks.
- Test concept index manager: verify OpenSearch indexing and search functionality.
- Test chunking pipeline: verify semantic chunking with configurable profiles, chunk ID stability, and metadata propagation.
- Test neighbor merging: verify similarity thresholds and merge constraints.
- Test guardrails: verify list item grouping, table preservation, and code block handling.
- Achieve 100% coverage for `src/Medical_KG/pdf/`, `src/Medical_KG/catalog/`, and `src/Medical_KG/chunking/`.

## Impact

- Affected specs: `testing` (MODIFIED: Subsystem Test Depth to include PDF, catalog, and chunking coverage requirements)
- Affected code: `tests/pdf/` (new directory), `tests/catalog/test_concept_catalog.py` (expand), `tests/chunking/test_semantic_chunker.py` (expand), `src/Medical_KG/pdf/`, `src/Medical_KG/catalog/`, `src/Medical_KG/chunking/`, `tests/conftest.py`
- Risks: PDF parsing is complex and sensitive to document structure; mitigation via diverse test documents covering tables, equations, multi-column layouts.
