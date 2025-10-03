# Implementation Tasks

## 1. JSON Schema Definitions

- [x] 1.1 Define facets.common.v1.json (Span, Code shared types)
- [x] 1.2 Define pico.v1.json (population, interventions[], comparators[], outcomes[], timeframe, evidence_spans[])
- [x] 1.3 Define effects.v1.json (type HR/RR/OR/MD/SMD, value, ci_low, ci_high, p_value, n_total, arm_sizes, model, time_unit_ucum, evidence_spans[])
- [x] 1.4 Define ae.v1.json (term, meddra_pt, grade 1-5, count, denom, arm, serious, onset_days, evidence_spans[])
- [x] 1.5 Define dose.v1.json (drug{rxcui, label}, amount, unit UCUM, route, frequency_per_day, duration_days, evidence_spans[])
- [x] 1.6 Define eligibility.v1.json (type inclusion/exclusion, criteria[]{text, logic{age, lab, condition, temporal}}, evidence_spans[])

## 2. LLM Extractor Prompts

- [x] 2.1 PICO prompt (system: extract Population, Interventions with dose, Comparators, Outcomes, Timeframe; use exact words from text; normalize dose to UCUM only in output fields)
- [x] 2.2 Effects prompt (system: report effects where endpoint + numeric present; capture type, value, ci_low, ci_high, p_value, model; do NOT compute values)
- [x] 2.3 AE prompt (system: map to MedDRA PT if unambiguous; include grade if explicitly provided; extract count, denom, arm)
- [x] 2.4 Dose prompt (system: extract dosing regimen; normalize to {amount, unit UCUM, route, frequency_per_day, duration_days}; keep quote verbatim)
- [x] 2.5 Eligibility prompt (system: split inclusion/exclusion; fill logic when clearly present: age, lab thresholds with LOINC+UCUM, conditions with code system)
- [x] 2.6 Add global rules (no inference beyond text; return only JSON; include evidence_spans for every field; omit field if not present verbatim)

## 3. LLM Extractor Implementation

- [x] 3.1 Implement PICO extractor (temperature=0.1; max_tokens=900)
- [x] 3.2 Implement Effects extractor (temperature=0.0; max_tokens=700)
- [x] 3.3 Implement AE extractor (temperature=0.1; max_tokens=700)
- [x] 3.4 Implement Dose extractor (temperature=0.1; max_tokens=600)
- [x] 3.5 Implement Eligibility extractor (temperature=0.1; max_tokens=800)
- [x] 3.6 Add retry logic (invalid JSON → repair pass with error feedback; max 2 retries)

## 4. Normalizers

- [x] 4.1 Numbers: strip thousands separators; parse "0.61–0.95" → ci_low=0.61, ci_high=0.95; "p<0.001" → ".<0.001"
- [x] 4.2 Units: map to UCUM (e.g., "mg q12h" → amount=X, frequency_per_day=2); accept compact notations (mL/min/1.73m2 → UCUM)
- [x] 4.3 Routes: normalize synonyms (PO→oral, IV→intravenous); keep verbatim in evidence
- [x] 4.4 Drugs: resolve_drug(label) → [RxCUI, UNII] with confidence; attach to drug_codes
- [x] 4.5 Outcomes/Labs: resolve_lab(name) → LOINC if known; keep name only if not found
- [x] 4.6 AEs: resolve_meddra(term) → PT (prefer PT; fallback LLT)
- [x] 4.7 Confidence/acceptance: keep hidden __confidence per extraction; drop auto-codes with__confidence < 0.5

## 5. Parsers & Grammar

- [x] 5.1 CI parser: accept "a–b", "a - b", "(a, b)" formats
- [x] 5.2 Dose grammar: "{amount, unit, route, frequency_per_day, duration_days}" with UCUM normalization
- [x] 5.3 Lab threshold parser: "eGFR ≥ 45 mL/min/1.73m2" → {loinc:"48642-3", op:">=", value:45, unit:"mL/min/1.73m2"}
- [x] 5.4 Age parser: "18-85 years" → {gte:18, lte:85}
- [x] 5.5 Temporal parser: "within 3 months" → {op:"<=", days:90}

## 6. Span-Grounding Validation

- [x] 6.1 Every extraction must include evidence_spans[] with ≥1 span
- [x] 6.2 Each span must have doc_id, start, end (integers), quote (string)
- [x] 6.3 Validate start < end; start/end within chunk text length
- [x] 6.4 Reject extractions with missing evidence_spans (hard requirement)

## 7. SHACL-Style Pre-KG Checks

- [x] 7.1 UCUM validator: dose.unit, effects.time_unit_ucum, eligibility.lab.unit must be valid UCUM codes
- [x] 7.2 Effect sanity: HR/RR/OR > 0; ci_low ≤ value ≤ ci_high (with tolerance for rounding)
- [x] 7.3 AE completeness: if grade present, must be ∈ {1..5}
- [x] 7.4 Eligibility numeric: age.gte ≤ age.lte when both present
- [x] 7.5 Dead-letter queue (extraction_deadletter) for validation failures with reason

## 8. Token Budget Enforcement

- [x] 8.1 Count tokens using Qwen tokenizer
- [x] 8.2 If extraction >120 tokens (for facets) or >2000 tokens (for full extractions): drop optional fields, compress ranges, abbreviate routes
- [x] 8.3 Never drop evidence_spans

## 9. Write to Knowledge Graph

- [x] 9.1 Create :EvidenceVariable nodes (MERGE on id; SET population_json, interventions_json, comparators_json, outcomes_json, timeframe, spans_json)
- [x] 9.2 Create :Evidence nodes (MERGE on id; SET type, value, ci_low, ci_high, p_value, n_total, arm_sizes_json, model, time_unit_ucum, spans_json, certainty)
- [x] 9.3 Create :AdverseEvent nodes (MERGE on pt_code or pt; link to :Study/:Arm via :HAS_AE with grade, count, denom, serious, onset_days)
- [x] 9.4 Create :Intervention nodes with :HAS_DOSE edges (amount, unit, route, frequency_per_day, duration_days, loinc_section if from SPL)
- [x] 9.5 Create :EligibilityConstraint nodes (MERGE on id; SET type, logic_json, human_text; link to :Study)
- [x] 9.6 Link all to :Document/:Study via :REPORTS
- [x] 9.7 Link to :ExtractionActivity (provenance: model, version, prompt_hash, schema_hash, ts)

## 10. Chunk Selection & Routing

- [x] 10.1 PICO: select chunks from Abstract, Methods, Registry sections
- [x] 10.2 Effects: select chunks from Results sections, Outcome tables
- [x] 10.3 AEs: select chunks from AE tables, Adverse Reactions sections
- [x] 10.4 Dose: select chunks from SPL Dosage sections, trial Arms sections
- [x] 10.5 Eligibility: select chunks from ClinicalTrials.gov Eligibility sections, not SPL Contraindications

## 11. Provenance Envelope

- [x] 11.1 Wrap all extraction outputs with activity metadata: {model, version, prompt_hash, schema_hash, ts, extracted_at, chunk_ids[]}
- [x] 11.2 Store provenance in :ExtractionActivity nodes
- [x] 11.3 Link extractions to activities via :WAS_GENERATED_BY

## 12. Evaluation & Metrics

- [x] 12.1 PICO completeness: fraction with all {population, interventions, outcomes} present; target ≥0.85
- [x] 12.2 Effect F1: exact (type, value, ci_low, ci_high match); relaxed (tolerate rounding abs err ≤0.01); target ≥0.80 relaxed
- [x] 12.3 AE mapping accuracy: (PT + grade) vs gold; target ≥0.80
- [x] 12.4 Dose normalization: UCUM correctness ≥0.95; schedule fields ≥0.90
- [x] 12.5 Eligibility logic accuracy: numeric thresholds exact ≥0.90; condition/lab code mapping ≥0.85

## 13. Testing

- [x] 13.1 Unit tests for normalizers (numbers, units, routes, parsers)
- [x] 13.2 Unit tests for each schema validator (JSON Schema + SHACL checks)
- [x] 13.3 Integration tests (sample chunks → extractor → normalizer → validator → KG write)
- [x] 13.4 Test with gold annotations (compute completeness, F1, accuracy per extraction type)
- [x] 13.5 Test error handling (invalid JSON, missing spans, SHACL violations → dead-letter)

## 14. Documentation

- [x] 14.1 Document each extractor prompt with examples (positive/negative cases)
- [x] 14.2 Create extraction pipeline guide (chunk selection, routing, post-processing)
- [x] 14.3 Document normalizers and parsers (UCUM mapping, dose grammar, lab thresholds)
- [x] 14.4 Write runbook for low extraction quality (review prompts, tune schemas, add few-shot examples)
