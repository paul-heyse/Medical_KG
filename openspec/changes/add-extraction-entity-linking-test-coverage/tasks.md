# Implementation Tasks

## 1. Test Fixtures & Mocks

- [x] 1.1 Create sample clinical text snippets for each extraction type (PICO, effect, AE, dose, eligibility)
- [x] 1.2 Create sample extraction payloads with valid/invalid data
- [x] 1.3 Mock LLM responses for extraction (JSON payloads)
- [x] 1.4 Mock spaCy NER model: return mock entities with spans
- [x] 1.5 Mock UMLS/RxNorm/SNOMED lookups: return candidate concepts

## 2. Extraction Service Tests

- [x] 2.1 Test extraction orchestration: verify routing to correct extractors by section
- [x] 2.2 Test retry logic: verify retries on transient failures
- [x] 2.3 Test dead-letter handling: verify invalid extractions are logged and skipped
- [x] 2.4 Test envelope creation: verify metadata (model, version, prompt_hash, schema_hash)
- [x] 2.5 Test chunk batching: verify processing multiple chunks in one envelope

## 3. Extraction Normalizer Tests

- [x] 3.1 Test PICO normalization: verify deduplication of interventions/comparators/outcomes
- [x] 3.2 Test effect normalization: verify CI parsing, p-value extraction, count/denom extraction
- [x] 3.3 Test AE normalization: verify MedDRA resolution, count/denom extraction, serious flag detection
- [x] 3.4 Test dose normalization: verify drug resolution, unit standardization, route mapping, frequency mapping
- [x] 3.5 Test eligibility normalization: verify age logic parsing, lab threshold parsing, temporal constraint parsing

## 4. Extraction Parser Tests

- [x] 4.1 Test CI pattern: `"95% CI: 1.2-3.4"` → `(1.2, 3.4)`
- [x] 4.2 Test p-value pattern: `"p < 0.05"` → `"<0.05"`, `"p = 0.001"` → `"=0.001"`
- [x] 4.3 Test count pattern: `"12/50 patients"` → `(12, 50)`
- [x] 4.4 Test age range: `"18-65 years"` → `{"gte": 18, "lte": 65}`
- [x] 4.5 Test lab threshold: `"creatinine > 2.0 mg/dL"` → `{"analyte": "creatinine", "op": ">", "value": 2.0, "unit": "mg/dL"}`
- [x] 4.6 Test temporal constraint: `"within 6 months"` → `{"op": "<=", "days": 180}`
- [x] 4.7 Use `hypothesis` to generate edge cases (whitespace, unicode, mixed formats)

## 5. Extraction Validator Tests

- [x] 5.1 Test span validation: verify spans within chunk bounds
- [x] 5.2 Test span quote mismatch: verify error when quote doesn't match chunk text
- [x] 5.3 Test dose unit validation: verify error when unit provided without amount
- [x] 5.4 Test effect CI consistency: verify error when value outside CI bounds
- [x] 5.5 Test eligibility age range: verify error when gte > lte
- [x] 5.6 Test token budget: verify error when extraction exceeds facet or full budget

## 6. Extraction KG Builder Tests

- [x] 6.1 Test PICO → KG: verify EvidenceVariable node creation with JSON properties
- [x] 6.2 Test effect → KG: verify Evidence node creation with outcome relationship
- [x] 6.3 Test AE → KG: verify AdverseEvent node and HAS_AE relationship to Study
- [x] 6.4 Test dose → KG: verify Intervention node with dose dictionary
- [x] 6.5 Test eligibility → KG: verify EligibilityConstraint node with logic JSON
- [x] 6.6 Test extraction activity linkage: verify WAS_GENERATED_BY relationships

## 7. Entity Linking NER Tests

- [x] 7.1 Test entity detection: verify disease, drug, gene entities are identified
- [x] 7.2 Test boundary detection: verify entity spans are accurate
- [x] 7.3 Test overlapping entities: verify longest match wins
- [x] 7.4 Test abbreviation expansion: verify "MI" → "myocardial infarction"
- [x] 7.5 Test negation detection: verify "no cancer" doesn't link "cancer"

## 8. Candidate Generation Tests

- [x] 8.1 Test exact match: "aspirin" → RxNorm CUI
- [x] 8.2 Test fuzzy match: "aspirn" → "aspirin" → RxNorm CUI
- [x] 8.3 Test ranking: verify candidates ranked by edit distance and concept frequency
- [x] 8.4 Test no candidates: verify empty result when no matches found
- [x] 8.5 Test caching: verify repeated lookups return cached results

## 9. Entity Linking Decision Tests

- [x] 9.1 Test high-confidence link: verify single candidate above threshold is selected
- [x] 9.2 Test low-confidence link: verify ambiguous candidates trigger LLM disambiguation
- [x] 9.3 Test no-link decision: verify entities below threshold are not linked
- [x] 9.4 Test context-based disambiguation: verify LLM uses surrounding text

## 10. LLM Disambiguation Tests

- [x] 10.1 Mock LLM call: verify prompt includes entity, candidates, and context
- [x] 10.2 Test response parsing: verify selected candidate is extracted from JSON
- [x] 10.3 Test LLM failure: verify fallback to highest-ranked candidate
- [x] 10.4 Test LLM timeout: verify timeout handling and fallback

## 11. Coverage & Validation

- [ ] 11.1 Run `pytest tests/extraction/ tests/entity_linking/ --cov=src/Medical_KG/extraction --cov=src/Medical_KG/entity_linking --cov-report=term-missing`
- [ ] 11.2 Verify 100% coverage for all extraction and entity linking modules
- [x] 11.3 Ensure no LLM or UMLS calls in test suite (mock all external dependencies)
- [x] 11.4 Document extraction and entity linking test patterns in respective README files
