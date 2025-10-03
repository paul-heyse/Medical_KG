# Implementation Tasks

## 1. IrBuilder Signature Extension

- [x] 1.1 Add `raw: AdapterDocumentPayload | None = None` parameter to `IrBuilder.build()`
- [x] 1.2 Import `AdapterDocumentPayload` union from `ingestion/types`
- [x] 1.3 Add conditional logic to route to payload extractors when raw is not None
- [x] 1.4 Verify backward compatibility: run existing IR tests without modifications

## 2. Payload Extractor Implementation

- [x] 2.1 Implement `_extract_from_literature(raw: LiteratureDocumentPayload)` method
- [x] 2.2 Extract PMC sections as IR blocks with section metadata
- [x] 2.3 Extract PubMed MeSH terms as provenance metadata
- [x] 2.4 Implement `_extract_from_clinical(raw: ClinicalCatalogDocumentPayload)` method
- [x] 2.5 Extract clinical trial arms and outcomes as structured blocks
- [x] 2.6 Implement `_extract_from_guidelines(raw: GuidelineDocumentPayload)` method (optional priority)

## 3. IRValidator Payload-Aware Validation

- [x] 3.1 Add optional payload parameter to `IRValidator.validate_document()`
- [x] 3.2 Implement source-specific validation for clinical payloads (NCT ID presence)
- [x] 3.3 Implement source-specific validation for literature payloads (PMID/PMCID presence)

## 4. Integration Testing

- [x] 4.1 Write integration test for PubMed Document→DocumentIR with typed payload
- [x] 4.2 Write integration test for PMC Document→DocumentIR with sections extraction
- [x] 4.3 Write integration test for ClinicalTrials Document→DocumentIR with structured blocks
- [x] 4.4 Test backward compatibility: IR construction without payloads still works
- [x] 4.5 Verify extracted blocks pass IRValidator checks

## 5. Documentation & Review

- [x] 5.1 Update `ir/builder.py` docstrings to explain payload usage
- [x] 5.2 Add examples to module docstring showing payload-enabled vs legacy usage
- [x] 5.3 Update `docs/ir_pipeline.md` with typed payload integration section
- [x] 5.4 Run `mypy --strict` on ir/ and confirm no new errors
