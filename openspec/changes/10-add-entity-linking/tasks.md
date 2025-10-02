# Implementation Tasks

## 1. NER Stack Setup

- [x] 1.1 Install scispaCy (en_core_sci_sm or en_core_sci_md)
- [x] 1.2 Add custom entity types (drug, dose, route, frequency, lab_value, adverse_event, eligibility, outcome)
- [x] 1.3 Train/fine-tune custom heads on medical corpora if needed
- [x] 1.4 Configure QuickUMLS (if UMLS licensed; jaccard threshold 0.7; stemming; window size ≤6 tokens)

## 2. Deterministic ID Detectors

- [x] 2.1 Implement regex detectors (RxCUI numeric, UNII 10-char alphanumeric, NCT NCT\d{8}, DOI 10.\d+/.+, LOINC \d{1,7}-\d, GTIN-14 \d{14})
- [x] 2.2 Add checksum validators (SNOMED Verhoeff, GTIN-14 mod-10, DOI format)
- [x] 2.3 Create deterministic candidate with score=1.0 when ID format valid

## 3. Candidate Generation

- [x] 3.1 Implement dictionary lookup (exact + normalized match against Concept Catalog labels/synonyms via OpenSearch)
- [x] 3.2 Implement SPLADE sparse search (expand mention text; search concepts_v1 index; top-K=20)
- [x] 3.3 Implement dense KNN search (embed mention + context ±2 sentences via Qwen; search Neo4j concept_qwen_idx; top-K=20)
- [x] 3.4 Aggregate candidates via RRF (k=60) → top-K=20 final candidates
- [x] 3.5 Attach candidate metadata (iri, codes[], label, synonyms[], definition, license_bucket)

## 4. LLM Adjudication Service

- [x] 4.1 Define el_adjudicator.schema.json (chosen_id, ontology, score 0-1, evidence_span, alternates[], notes)
- [x] 4.2 Create adjudication prompt (system: "You are a medical entity linker. Prefer deterministic IDs. Return only valid JSON with evidence spans.")
- [x] 4.3 Implement LLM call (temperature=0.0-0.2; max_tokens=600; function-calling mode)
- [x] 4.4 Add retry logic (invalid JSON → repair pass with error feedback; max 2 retries)

## 5. Decision Rules & Post-Processing

- [x] 5.1 Accept if score ≥ 0.70 AND (if ID) validator passes
- [x] 5.2 If multiple accepted with same ontology → choose most specific (deepest in hierarchy)
- [x] 5.3 If none accepted → add to review queue with top-5 alternates
- [x] 5.4 Mark confidence on MENTIONS edge

## 6. Clinical NLP Guardrails

- [x] 6.1 Implement ConText/NegEx (detect negation triggers: "no", "denies", "without"; uncertainty: "possible", "probable")
- [x] 6.2 Tag mentions as negated=true or hypothetical=true
- [x] 6.3 Section-aware filtering (boost "ae" type in Adverse Reactions sections; boost "eligibility" in Inclusion/Exclusion)
- [x] 6.4 Handle co-reference (lightweight: "the study drug" → resolve to intervention mention in same chunk)

## 7. Span Cleanup & Expansion

- [x] 7.1 Expand spans to include adjacent units (e.g., "10" + "mg" → "10 mg")
- [x] 7.2 Collapse overlapping matches by highest specificity (prefer "enalapril maleate" over "enalapril" if both backed by concepts)
- [x] 7.3 Validate span offsets (start < end; within chunk text length)

## 8. Write to Knowledge Graph

- [x] 8.1 Create (:Chunk)-[:MENTIONS {confidence, start, end, quote, negated?, hypothetical?}]->(:Concept) edges
- [x] 8.2 For deterministic IDs: create (:Chunk)-[:HAS_IDENTIFIER]->(:Identifier {scheme, code})
- [x] 8.3 Batch writes (1000 edges/tx via APOC)
- [x] 8.4 Link to :ExtractionActivity (provenance)

## 9. Review Queue

- [x] 9.1 Create review_queue table/collection (mention_id, chunk_id, text, candidates[], reason, status)
- [x] 9.2 Add items when score < 0.70 or conflicts detected
- [x] 9.3 Implement review UI requirements (PDF with span highlights; one-click accept/correct/reject)
- [x] 9.4 Create curated crosswalks from corrections (store as :SAME_AS edges with evidence="manual")

## 10. Evaluation & Metrics

- [x] 10.1 Compute ID accuracy (deterministic: RxCUI, UNII, NCT, LOINC, UDI vs gold; target ≥0.95)
- [x] 10.2 Compute concept EL accuracy (micro-avg vs gold UMLS/SNOMED/LOINC; target ≥0.85)
- [x] 10.3 Compute coverage (fraction of mentions linked with confidence ≥ threshold; target ≥0.80)
- [x] 10.4 Compute calibration (reliability diagram; ECE ≤ 0.05 at threshold 0.70)
- [x] 10.5 Monitor abstention rate (score < threshold; target ≤ 0.15)

## 11. Error Handling

- [x] 11.1 LLM fails or returns invalid JSON → retry once; fallback to dictionary + deterministic ID only (mark confidence=0.49)
- [x] 11.2 Candidate generation fails → log and skip mention (don't block pipeline)
- [x] 11.3 KG write fails → dead-letter queue with payload

## 12. Performance & Throughput

- [x] 12.1 Batch NER (process 100 chunks in parallel)
- [x] 12.2 Batch candidate generation (group by mention type)
- [x] 12.3 Batch LLM adjudication (up to 20 candidates/mention; max 300 mentions/doc per pass)
- [x] 12.4 Target throughput: ≥2,000 tokens/s/GPU for NER + candidate generation

## 13. Testing

- [x] 13.1 Unit tests for ID validators (positive/negative test sets)
- [x] 13.2 Unit tests for ConText/NegEx rules
- [x] 13.3 Integration test (sample chunks → NER → candidates → adjudication → KG write)
- [x] 13.4 Test with gold annotations (compute accuracy, coverage, calibration)
- [x] 13.5 Test review queue workflow (low-confidence → queue → manual correction → crosswalk)

## 14. Documentation

- [x] 14.1 Document NER pipeline and custom entity types
- [x] 14.2 Create adjudication prompt examples (positive/negative cases)
- [x] 14.3 Write runbook for low acceptance rate (tune threshold, retrain tagger)
- [x] 14.4 Document review queue SLA (5 business days for critical items)
