## Why

Extraction and entity linking modules have partial coverage. Extraction service, normalizers, parsers, validators, and KG integration are tested minimally. Entity linking NER, candidate generation, decision logic, and LLM disambiguation are untested. These modules perform critical data extraction and normalization—errors here propagate to all downstream systems.

## What Changes

- Add unit tests for `ClinicalExtractionService`: verify extraction orchestration, retry logic, and dead-letter handling.
- Test extraction normalizers: verify PICO, effect, AE, dose, and eligibility normalization logic.
- Test extraction parsers: verify regex patterns for CI, p-values, counts, age ranges, lab thresholds, and temporal constraints.
- Test extraction validators: verify span validation, dose unit checks, effect CI consistency, and eligibility age ranges.
- Test extraction KG builder: verify Cypher statement generation for all extraction types.
- Test entity linking NER: mock spaCy model, verify entity detection and boundary detection.
- Test candidate generation: verify UMLS/RxNorm/SNOMED lookups, fuzzy matching, and ranking.
- Test entity linking decision logic: verify confidence scoring, disambiguation, and fallback rules.
- Test LLM-based disambiguation: mock LLM calls, verify prompt construction and response parsing.
- Achieve 100% coverage for `src/Medical_KG/extraction/` and `src/Medical_KG/entity_linking/`.

## Impact

- Affected specs: `testing` (MODIFIED: Subsystem Test Depth to include extraction and entity linking coverage requirements)
- Affected code: `tests/extraction/` (expand), `tests/entity_linking/` (new directory), `src/Medical_KG/extraction/`, `src/Medical_KG/entity_linking/`, `tests/conftest.py`
- Risks: extraction logic is complex and regex-heavy; mitigation via property-based testing with `hypothesis` for parser edge cases.
