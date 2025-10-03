# Implementation Tasks

## 1. Type Guard Implementation

- [ ] 1.1 Define `is_terminology_payload()` type guard for TerminologyDocumentPayload union
- [ ] 1.2 Define `is_literature_payload()` type guard for LiteratureDocumentPayload union
- [ ] 1.3 Define `is_clinical_payload()` type guard for ClinicalCatalogDocumentPayload union
- [ ] 1.4 Define `is_guideline_payload()` type guard for GuidelineDocumentPayload union
- [ ] 1.5 Define `is_knowledge_base_payload()` type guard for KnowledgeBaseDocumentPayload union
- [ ] 1.6 Add fine-grained guards for specific payloads (e.g., `is_pubmed_payload`, `is_mesh_payload`)

## 2. Adapter Refactoring

- [ ] 2.1 Update `PubMedAdapter.validate()` to use `is_pubmed_payload()` guard (line ~138)
- [ ] 2.2 Update `PmcAdapter.validate()` to use `is_pmc_payload()` guard (line ~290)
- [ ] 2.3 Update `MedRxivAdapter.validate()` to use `is_medrxiv_payload()` guard (line ~423)
- [ ] 2.4 Update `SnomedAdapter.validate()` to use type guard (line 246)
- [ ] 2.5 Update `ClinicalTrialsGovAdapter.validate()` to use type guard (line 225)
- [ ] 2.6 Review all adapters for remaining `isinstance(document.raw, Mapping)` patterns and replace

## 3. Testing & Validation

- [ ] 3.1 Write unit tests for each type guard function (positive and negative cases)
- [ ] 3.2 Test that type guards correctly narrow types for mypy
- [ ] 3.3 Ensure validate() methods no longer use isinstance checks
- [ ] 3.4 Run `mypy --strict` on ingestion module and confirm type narrowing works
- [ ] 3.5 Add integration test verifying type guards reject mismatched payloads
