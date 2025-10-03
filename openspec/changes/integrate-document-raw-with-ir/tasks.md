# Implementation Tasks

## 1. IrBuilder Signature Extension

- [ ] 1.1 Add `raw: AdapterDocumentPayload | None = None` parameter to `IrBuilder.build()`
- [ ] 1.2 Import `AdapterDocumentPayload` union from `ingestion/types`
- [ ] 1.3 Add conditional logic to route to payload extractors when raw is not None
- [ ] 1.4 Verify backward compatibility: run existing IR tests without modifications

## 2. Payload Extractor Implementation

- [ ] 2.1 Implement `_extract_from_literature(raw: LiteratureDocumentPayload)` method
- [ ] 2.2 Extract PMC sections as IR blocks with section metadata
- [ ] 2.3 Extract PubMed MeSH terms as provenance metadata
- [ ] 2.4 Implement `_extract_from_clinical(raw: ClinicalCatalogDocumentPayload)` method
- [ ] 2.5 Extract clinical trial arms and outcomes as structured blocks
- [ ] 2.6 Implement `_extract_from_guidelines(raw: GuidelineDocumentPayload)` method (optional priority)

## 3. IRValidator Payload-Aware Validation

- [ ] 3.1 Add optional payload parameter to `IRValidator.validate_document()`
- [ ] 3.2 Implement source-specific validation for clinical payloads (NCT ID presence)
- [ ] 3.3 Implement source-specific validation for literature payloads (PMID/PMCID presence)

## 4. Integration Testing

- [ ] 4.1 Write integration test for PubMed Document→DocumentIR with typed payload
- [ ] 4.2 Write integration test for PMC Document→DocumentIR with sections extraction
- [ ] 4.3 Write integration test for ClinicalTrials Document→DocumentIR with structured blocks
- [ ] 4.4 Test backward compatibility: IR construction without payloads still works
- [ ] 4.5 Verify extracted blocks pass IRValidator checks

## 5. Documentation & Review

- [ ] 5.1 Update `ir/builder.py` docstrings to explain payload usage
- [ ] 5.2 Add examples to module docstring showing payload-enabled vs legacy usage
- [ ] 5.3 Update `docs/ir_pipeline.md` with typed payload integration section
- [ ] 5.4 Run `mypy --strict` on ir/ and confirm no new errors
