# Implementation Tasks

## 1. NER Stack Setup

- [ ] 1.1 Install scispaCy (en_core_sci_sm or en_core_sci_md)
- [ ] 1.2 Add custom entity types (drug, dose, route, frequency, lab_value, adverse_event, eligibility, outcome)
- [ ] 1.3 Train/fine-tune custom heads on medical corpora if needed
- [ ] 1.4 Configure QuickUMLS (if UMLS licensed; jaccard threshold 0.7; stemming; window size ≤6 tokens)

## 2. Deterministic ID Detectors

- [ ] 2.1 Implement regex detectors (RxCUI numeric, UNII 10-char alphanumeric, NCT NCT\d{8}, DOI 10.\d+/.+, LOINC \d{1,7}-\d, GTIN-14 \d{14})
- [ ] 2.2 Add checksum validators (SNOMED Verhoeff, GTIN-14 mod-10, DOI format)
- [ ] 2.3 Create deterministic candidate with score=1.0 when ID format valid

## 3. Candidate Generation

- [ ] 3.1 Implement dictionary lookup (exact + normalized match against Concept Catalog labels/synonyms via OpenSearch)
- [ ] 3.2 Implement SPLADE sparse search (expand mention text; search concepts_v1 index; top-K=20)
- [ ] 3.3 Implement dense KNN search (embed mention + context ±2 sentences via Qwen; search Neo4j concept_qwen_idx; top-K=20)
- [ ] 3.4 Aggregate candidates via RRF (k=60) → top-K=20 final candidates
- [ ] 3.5 Attach candidate metadata (iri, codes[], label, synonyms[], definition, license_bucket)

## 4. LLM Adjudication Service

- [ ] 4.1 Define el_adjudicator.schema.json (chosen_id, ontology, score 0-1, evidence_span, alternates[], notes)
- [ ] 4.2 Create adjudication prompt (system: "You are a medical entity linker. Prefer deterministic IDs. Return only valid JSON with evidence spans.")
- [ ] 4.3 Implement LLM call (temperature=0.0-0.2; max_tokens=600; function-calling mode)
- [ ] 4.4 Add retry logic (invalid JSON → repair pass with error feedback; max 2 retries)

## 5. Decision Rules & Post-Processing

- [ ] 5.1 Accept if score ≥ 0.70 AND (if ID) validator passes
- [ ] 5.2 If multiple accepted with same ontology → choose most specific (deepest in hierarchy)
- [ ] 5.3 If none accepted → add to review queue with top-5 alternates
- [ ] 5.4 Mark confidence on MENTIONS edge

## 6. Clinical NLP Guardrails

- [ ] 6.1 Implement ConText/NegEx (detect negation triggers: "no", "denies", "without"; uncertainty: "possible", "probable")
- [ ] 6.2 Tag mentions as negated=true or hypothetical=true
- [ ] 6.3 Section-aware filtering (boost "ae" type in Adverse Reactions sections; boost "eligibility" in Inclusion/Exclusion)
- [ ] 6.4 Handle co-reference (lightweight: "the study drug" → resolve to intervention mention in same chunk)

## 7. Span Cleanup & Expansion

- [ ] 7.1 Expand spans to include adjacent units (e.g., "10" + "mg" → "10 mg")
- [ ] 7.2 Collapse overlapping matches by highest specificity (prefer "enalapril maleate" over "enalapril" if both backed by concepts)
- [ ] 7.3 Validate span offsets (start < end; within chunk text length)

## 8. Write to Knowledge Graph

- [ ] 8.1 Create (:Chunk)-[:MENTIONS {confidence, start, end, quote, negated?, hypothetical?}]->(:Concept) edges
- [ ] 8.2 For deterministic IDs: create (:Chunk)-[:HAS_IDENTIFIER]->(:Identifier {scheme, code})
- [ ] 8.3 Batch writes (1000 edges/tx via APOC)
- [ ] 8.4 Link to :ExtractionActivity (provenance)

## 9. Review Queue

- [ ] 9.1 Create review_queue table/collection (mention_id, chunk_id, text, candidates[], reason, status)
- [ ] 9.2 Add items when score < 0.70 or conflicts detected
- [ ] 9.3 Implement review UI requirements (PDF with span highlights; one-click accept/correct/reject)
- [ ] 9.4 Create curated crosswalks from corrections (store as :SAME_AS edges with evidence="manual")

## 10. Evaluation & Metrics

- [ ] 10.1 Compute ID accuracy (deterministic: RxCUI, UNII, NCT, LOINC, UDI vs gold; target ≥0.95)
- [ ] 10.2 Compute concept EL accuracy (micro-avg vs gold UMLS/SNOMED/LOINC; target ≥0.85)
- [ ] 10.3 Compute coverage (fraction of mentions linked with confidence ≥ threshold; target ≥0.80)
- [ ] 10.4 Compute calibration (reliability diagram; ECE ≤ 0.05 at threshold 0.70)
- [ ] 10.5 Monitor abstention rate (score < threshold; target ≤ 0.15)

## 11. Error Handling

- [ ] 11.1 LLM fails or returns invalid JSON → retry once; fallback to dictionary + deterministic ID only (mark confidence=0.49)
- [ ] 11.2 Candidate generation fails → log and skip mention (don't block pipeline)
- [ ] 11.3 KG write fails → dead-letter queue with payload

## 12. Performance & Throughput

- [ ] 12.1 Batch NER (process 100 chunks in parallel)
- [ ] 12.2 Batch candidate generation (group by mention type)
- [ ] 12.3 Batch LLM adjudication (up to 20 candidates/mention; max 300 mentions/doc per pass)
- [ ] 12.4 Target throughput: ≥2,000 tokens/s/GPU for NER + candidate generation

## 13. Testing

- [ ] 13.1 Unit tests for ID validators (positive/negative test sets)
- [ ] 13.2 Unit tests for ConText/NegEx rules
- [ ] 13.3 Integration test (sample chunks → NER → candidates → adjudication → KG write)
- [ ] 13.4 Test with gold annotations (compute accuracy, coverage, calibration)
- [ ] 13.5 Test review queue workflow (low-confidence → queue → manual correction → crosswalk)

## 14. Documentation

- [ ] 14.1 Document NER pipeline and custom entity types
- [ ] 14.2 Create adjudication prompt examples (positive/negative cases)
- [ ] 14.3 Write runbook for low acceptance rate (tune threshold, retrain tagger)
- [ ] 14.4 Document review queue SLA (5 business days for critical items)
