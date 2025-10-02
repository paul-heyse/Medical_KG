# Implementation Tasks

## 1. Facet Routing

- [x] 1.1 Implement facet type detector (majority vote of sentence clinical tags from chunker)
- [x] 1.2 Add deterministic rules (SPL Indications → pico; SPL Adverse Reactions → ae; CTG Outcome Measures → endpoint; SPL Dosage → dose)
- [x] 1.3 Add table header heuristics (columns contain {Outcome, HR, OR, RR} → endpoint; columns contain {AE, Grade, Incidence} → ae)
- [x] 1.4 Fallback to general if intent unclear
- [x] 1.5 Emit 0-N facet types per chunk (common: 1-2)

## 2. Facet JSON Schemas

- [x] 2.1 Define facet.pico.v1.json (population, interventions[], comparators[], outcomes[], timeframe, evidence_spans[], token_budget:120)
- [x] 2.2 Define facet.endpoint.v1.json (name, type HR/RR/OR/MD/SMD, value, ci_low, ci_high, p, n_total, arm_sizes, model, time_unit_ucum, outcome_codes[], evidence_spans[], token_budget:120)
- [x] 2.3 Define facet.ae.v1.json (term, meddra_pt, grade 1-5, arm, count, denom, serious, onset_days, evidence_spans[], token_budget:120)
- [x] 2.4 Define facet.dose.v1.json (drug_label, drug_codes[], amount, unit UCUM, route, frequency_per_day, duration_days, loinc_section, evidence_spans[], token_budget:120)
- [x] 2.5 Define facet.common.v1.json (Span, Code shared types)

## 3. LLM Facet Generators

- [ ] 3.1 PICO facet prompt (extract compact PICO; use exact words; ≤120 tokens; include evidence_spans)
- [ ] 3.2 Endpoint facet prompt (extract single outcome + metric; capture type, value, CI, p, N; ≤120 tokens)
- [ ] 3.3 AE facet prompt (map AE term to MedDRA PT; include grade if present; extract arm, count, denom; ≤120 tokens)
- [ ] 3.4 Dose facet prompt (extract dosing regimen; normalize to UCUM; ≤120 tokens)
- [ ] 3.5 Global rules (no inference; return only JSON; include evidence_spans; omit if not verbatim; ≤120 tokens)
- [x] 3.6 Implement generators (temperature=0.1; max_tokens=300 to allow buffer; retry on invalid JSON)

## 4. Token Budget Enforcement

- [ ] 4.1 Count tokens using Qwen tokenizer after LLM generation
- [ ] 4.2 If >120 tokens: drop optional fields (priority: narrative text → codes → model → arm sizes → alternates)
- [ ] 4.3 Compress ranges (CI as numbers only; remove spaces)
- [ ] 4.4 Abbreviate routes (PO, IV)
- [ ] 4.5 Never drop evidence_spans (hard requirement)
- [ ] 4.6 Fail validation if still >120 after compression

## 5. Normalizers (Post-LLM)

- [ ] 5.1 Numbers: parse "0.61–0.95" → ci_low=0.61, ci_high=0.95; "p<0.001" → ".<0.001"
- [ ] 5.2 Units: map to UCUM; keep verbatim in evidence
- [ ] 5.3 Routes: normalize synonyms; keep verbatim in evidence
- [ ] 5.4 Drugs: resolve_drug(label) → RxCUI/UNII with confidence; attach to drug_codes
- [ ] 5.5 Outcomes/Labs: resolve_lab(name) → LOINC if known
- [ ] 5.6 AEs: resolve_meddra(term) → PT
- [ ] 5.7 Drop auto-codes with __confidence < 0.5

## 6. Storage (Neo4j)

- [x] 6.1 Add properties to :Chunk (facet_pico_v1 string, facet_endpoint_v1 string[], facet_ae_v1 string[], facet_dose_v1 string[], facets_model_meta map)
- [x] 6.2 MERGE :Chunk and SET facet properties
- [x] 6.3 Store model metadata (model, version, prompt_hash, ts)

## 7. Indexing (OpenSearch)

- [x] 7.1 Add facet_json field (keyword + text multi-fields; copy all facet JSON strings)
- [x] 7.2 Add facet_type field (keyword; values: pico|endpoint|ae|dose|eligibility|general)
- [x] 7.3 Add facet_codes field (keyword[]; extract codes.code from all facets)
- [x] 7.4 Set BM25F boosts (facet_json: 1.6)
- [ ] 7.5 Include facets in SPLADE doc-side expansion (body + title_path + facet_json + table_lines)

## 8. Optional: Facet Embeddings

- [ ] 8.1 Compute Qwen embeddings for facet JSON (minified string)
- [ ] 8.2 Store as chunk.facet_embedding_qwen (optional; off by default to save space)
- [ ] 8.3 Create separate vector index for facet embeddings if enabled

## 9. Deduplication

- [ ] 9.1 Key facet:endpoint by (normalized_outcome_name|loinc, type, timeframe?)
- [ ] 9.2 Key facet:ae by (meddra_pt|term_lower, grade?, arm?)
- [ ] 9.3 Keep all originals but mark is_primary=true on highest confidence
- [ ] 9.4 Dedupe within document only (allow same facet across different documents)

## 10. QA & Failure Handling

- [ ] 10.1 Schema validation (reject non-conforming JSON; log with reason)
- [ ] 10.2 Span verification (every evidence_spans[*] must be within [0, len(text)))
- [ ] 10.3 Unit sanity (dose amount must be numeric if unit present; else drop unit)
- [ ] 10.4 Token budget check (fail if >120 after compression)
- [ ] 10.5 Escalation (chunks with 3 consecutive facet failures go to manual review queue)

## 11. APIs

- [x] 11.1 POST /facets/generate (body: {chunk_ids[]}; return: {facets_by_chunk{chunk_id: facets[]}})
- [x] 11.2 GET /chunks/{chunk_id} (include facets in response)
- [x] 11.3 POST /retrieve (filter by facet_type; boost facet_json field)

## 12. Testing

- [x] 12.1 Unit tests for each facet generator (sample chunks → verify JSON conforms to schema)
- [ ] 12.2 Unit tests for token budget enforcement (oversized facet → verify compression + validation)
- [ ] 12.3 Integration test (chunk → detect intent → generate facet → validate → store → index)
- [ ] 12.4 Test deduplication (two chunks with same endpoint → verify only one marked is_primary)
- [x] 12.5 Test retrieval boost (facet query → verify facet-tagged chunks rank higher)

## 13. Documentation

- [ ] 13.1 Document facet schemas with examples
- [ ] 13.2 Create facet generation guide (routing rules, prompt tuning, token budget management)
- [ ] 13.3 Document normalization rules (units, routes, codes)
- [ ] 13.4 Write runbook for facet quality issues (low completeness, schema violations)
