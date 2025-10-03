# Clinical Extraction Capability

## ADDED Requirements

### Requirement: PICO Extractor

The system SHALL extract Population, Intervention, Comparator, Outcome, and Timeframe from clinical study chunks with span grounding.

#### Scenario: Extract complete PICO

- **WHEN** chunk contains "Adults aged 18-75 with type 2 diabetes received metformin 1000mg BID vs placebo for 24 weeks to assess HbA1c reduction"
- **THEN** the system SHALL extract {population: "Adults aged 18-75 with type 2 diabetes", interventions: [{drug: "metformin", dose: "1000mg BID"}], comparators: ["placebo"], outcomes: ["HbA1c reduction"], timeframe: "24 weeks", evidence_spans: [...]}

#### Scenario: Partial PICO extraction

- **WHEN** chunk contains only population and outcomes
- **THEN** the system SHALL extract available fields and omit missing fields (do not infer)

#### Scenario: Span grounding enforcement

- **WHEN** extracting any PICO element
- **THEN** each field MUST include evidence_spans[] with {doc_id, start, end, quote} or be omitted

### Requirement: Effects Extractor

The system SHALL extract effect measures (HR, RR, OR, MD, SMD) with confidence intervals, p-values, and sample sizes.

#### Scenario: Extract hazard ratio

- **WHEN** chunk contains "HR 0.68 (95% CI 0.61-0.95, p=0.001, n=2,140)"
- **THEN** the system SHALL extract {type: "HR", value: 0.68, ci_low: 0.61, ci_high: 0.95, p_value: "=0.001", n_total: 2140, evidence_spans: [...]}

#### Scenario: Extract relative risk

- **WHEN** chunk contains "RR 1.23 (0.95–1.52)"
- **THEN** the system SHALL extract {type: "RR", value: 1.23, ci_low: 0.95, ci_high: 1.52, evidence_spans: [...]}

#### Scenario: No inference rule

- **WHEN** chunk mentions outcome but no numeric effect
- **THEN** the system SHALL NOT extract effect (omit rather than guess)

#### Scenario: Model and timepoint

- **WHEN** text specifies "Cox proportional hazards model at 12 months"
- **THEN** the system SHALL extract model="Cox proportional hazards", time_unit_ucum="mo", timepoint=12

### Requirement: Adverse Events Extractor

The system SHALL extract adverse events with MedDRA PT mapping, CTCAE grades, counts, and arm attribution.

#### Scenario: Extract graded AE

- **WHEN** chunk contains "Grade 3 nausea occurred in 12/100 patients in the treatment arm"
- **THEN** the system SHALL extract {term: "nausea", meddra_pt: "Nausea", grade: 3, count: 12, denom: 100, arm: "treatment", evidence_spans: [...]}

#### Scenario: Map to MedDRA PT

- **WHEN** extracting "vomiting"
- **THEN** the system SHALL resolve_meddra("vomiting") → PT "Vomiting" and include in meddra_pt field with confidence

#### Scenario: Serious AE flag

- **WHEN** text contains "serious adverse event" or "SAE"
- **THEN** the system SHALL set serious=true in extraction

#### Scenario: Onset timing

- **WHEN** text specifies "onset within 7 days"
- **THEN** the system SHALL extract onset_days=7

### Requirement: Dosing Extractor

The system SHALL extract dosing regimens with UCUM-normalized units, routes, frequencies, and durations.

#### Scenario: Extract complete regimen

- **WHEN** chunk contains "Enalapril 10 mg PO BID for 6 months"
- **THEN** the system SHALL extract {drug_label: "Enalapril", drug_codes: [{rxcui: "..."}], amount: 10, unit: "mg", route: "PO", frequency_per_day: 2, duration_days: 180, evidence_spans: [...]}

#### Scenario: UCUM normalization

- **WHEN** dose is "500mg q12h"
- **THEN** the system SHALL normalize to {amount: 500, unit: "mg" (UCUM), frequency_per_day: 2}

#### Scenario: Complex frequency parsing

- **WHEN** dose is "Loading dose 300mg, then 75mg daily"
- **THEN** the system SHALL extract maintenance dose and note loading dose in metadata

#### Scenario: SPL section attribution

- **WHEN** extracting from DailyMed SPL
- **THEN** the system SHALL include loinc_section (e.g., "34068-7" for Dosage and Administration)

### Requirement: Eligibility Extractor

The system SHALL extract inclusion/exclusion criteria with structured logic for age, labs, conditions, and temporal constraints.

#### Scenario: Extract age range

- **WHEN** criteria contains "Ages 18-65 years"
- **THEN** the system SHALL extract {type: "inclusion", text: "Ages 18-65 years", logic: {age: {gte: 18, lte: 65}}, evidence_spans: [...]}

#### Scenario: Extract lab threshold

- **WHEN** criteria contains "eGFR ≥ 45 mL/min/1.73m²"
- **THEN** the system SHALL extract {type: "inclusion", text: "...", logic: {lab: {loinc: "48642-3", op: ">=", value: 45, unit: "mL/min/1.73m2" (UCUM)}}, evidence_spans: [...]}

#### Scenario: Extract condition

- **WHEN** criteria contains "Diagnosis of type 2 diabetes"
- **THEN** the system SHALL extract {type: "inclusion", text: "...", logic: {condition: {label: "type 2 diabetes", codes: [{system: "SNOMED", code: "44054006"}]}}, evidence_spans: [...]}

#### Scenario: Extract temporal constraint

- **WHEN** criteria contains "MI within past 3 months"
- **THEN** the system SHALL extract {type: "exclusion", text: "...", logic: {temporal: {event: "MI", op: "<=", days: 90}}, evidence_spans: [...]}

### Requirement: JSON Schema Validation

The system SHALL validate all extractions against strict JSON schemas before writing to KG.

#### Scenario: PICO schema validation

- **WHEN** validating PICO extraction
- **THEN** the system SHALL verify against pico.v1.json schema requiring evidence_spans[], optional interventions/comparators/outcomes fields

#### Scenario: Effects schema validation

- **WHEN** validating effect extraction
- **THEN** the system SHALL verify against effects.v1.json schema requiring type, value, evidence_spans[] and optional ci_low, ci_high, p_value

#### Scenario: Required evidence spans

- **WHEN** any extraction lacks evidence_spans[]
- **THEN** the system SHALL reject with ValidationError "Missing evidence_spans"

### Requirement: Normalizers and Parsers

The system SHALL normalize numeric values, units, codes, and drug names for KG consistency.

#### Scenario: Parse confidence intervals

- **WHEN** text contains "0.61–0.95", "0.61 - 0.95", or "(0.61, 0.95)"
- **THEN** the system SHALL parse to ci_low=0.61, ci_high=0.95

#### Scenario: Parse p-values

- **WHEN** text contains "p<0.001", "p = 0.03", or "p-value 0.045"
- **THEN** the system SHALL normalize to ".<0.001", "=0.03", "=0.045" respectively

#### Scenario: Normalize units to UCUM

- **WHEN** dose contains "mg q12h", "mL/min/1.73m2", "IU/day"
- **THEN** the system SHALL map to valid UCUM codes and store in unit field

#### Scenario: Resolve drug names

- **WHEN** extracting drug="enalapril maleate"
- **THEN** the system SHALL call resolve_drug() and attach drug_codes=[{rxcui: "...", unii: "..."}] with confidence

#### Scenario: Resolve labs to LOINC

- **WHEN** extracting lab="HbA1c"
- **THEN** the system SHALL call resolve_lab() and attach loinc="4548-4" if confident

#### Scenario: Resolve AEs to MedDRA

- **WHEN** extracting AE="headache"
- **THEN** the system SHALL call resolve_meddra() and attach meddra_pt="Headache" with confidence

### Requirement: SHACL-Style Pre-KG Checks

The system SHALL validate extractions against integrity rules before writing to KG.

#### Scenario: UCUM validation

- **WHEN** extraction contains unit field
- **THEN** the system SHALL verify unit is valid UCUM code or reject to dead-letter queue

#### Scenario: Effect value sanity

- **WHEN** effect type is HR/RR/OR
- **THEN** the system SHALL verify value > 0 and ci_low ≤ value ≤ ci_high (within rounding tolerance)

#### Scenario: AE grade range

- **WHEN** AE extraction includes grade
- **THEN** the system SHALL verify grade ∈ {1, 2, 3, 4, 5} or reject

#### Scenario: Age range consistency

- **WHEN** eligibility includes age.gte and age.lte
- **THEN** the system SHALL verify age.gte ≤ age.lte or reject

#### Scenario: Dead-letter on violation

- **WHEN** validation fails
- **THEN** the system SHALL write to extraction_deadletter with {reason, payload_hash, timestamp}

### Requirement: Span-Grounding Validation

The system SHALL enforce span-grounding for all clinical assertions.

#### Scenario: Verify span presence

- **WHEN** extraction is created
- **THEN** each claim MUST have ≥1 evidence_span or be rejected

#### Scenario: Validate span offsets

- **WHEN** evidence_span includes {doc_id, start, end, quote}
- **THEN** the system SHALL verify start < end and offsets within chunk.text length

#### Scenario: Validate quote match

- **WHEN** evidence_span includes quote
- **THEN** the system SHALL verify quote matches chunk.text[start:end] exactly

#### Scenario: Hard rejection

- **WHEN** span validation fails
- **THEN** the system SHALL reject extraction with clear error message

### Requirement: Token Budget Enforcement

The system SHALL enforce token budgets for facets while allowing flexible sizes for full extractions.

#### Scenario: Facet token limit

- **WHEN** creating facet extraction (facet=true)
- **THEN** the system SHALL enforce ≤120 tokens using Qwen tokenizer

#### Scenario: Facet compression

- **WHEN** facet extraction exceeds 120 tokens
- **THEN** the system SHALL drop optional fields (priority: notes → alternates → model → arm_sizes) but never evidence_spans

#### Scenario: Full extraction flexibility

- **WHEN** creating full clinical extraction (facet=false)
- **THEN** the system SHALL allow up to 2000 tokens before compression

### Requirement: Write to Knowledge Graph

The system SHALL write validated extractions to Neo4j as structured nodes with provenance links.

#### Scenario: Create EvidenceVariable node

- **WHEN** PICO extraction validated
- **THEN** the system SHALL MERGE (:EvidenceVariable {id, population_json, interventions_json, comparators_json, outcomes_json, timeframe, spans_json})

#### Scenario: Create Evidence node

- **WHEN** effect extraction validated
- **THEN** the system SHALL MERGE (:Evidence {id, type, value, ci_low, ci_high, p_value, n_total, arm_sizes_json, model, time_unit_ucum, spans_json, certainty})

#### Scenario: Create AdverseEvent node

- **WHEN** AE extraction validated
- **THEN** the system SHALL MERGE (:AdverseEvent {id, term, meddra_pt, grade, count, denom, arm, serious, onset_days, spans_json})

#### Scenario: Link to source

- **WHEN** writing extraction nodes
- **THEN** the system SHALL CREATE (:Document|:Study)-[:REPORTS]->(:Evidence|:EvidenceVariable|:AdverseEvent)

#### Scenario: Link to activity

- **WHEN** writing extraction
- **THEN** the system SHALL CREATE (:Extraction)-[:WAS_GENERATED_BY]->(:ExtractionActivity {model, version, prompt_hash, schema_hash, ts})

### Requirement: Evaluation Metrics

The system SHALL compute extraction quality metrics against gold annotations.

#### Scenario: PICO completeness

- **WHEN** evaluating PICO extractions
- **THEN** the system SHALL compute fraction with all {population, interventions, outcomes} present (target ≥0.85)

#### Scenario: Effect F1 scores

- **WHEN** evaluating effect extractions
- **THEN** the system SHALL compute exact F1 (type, value, ci_low, ci_high match) and relaxed F1 (abs error ≤0.01) with target ≥0.80 relaxed

#### Scenario: AE mapping accuracy

- **WHEN** evaluating AE extractions
- **THEN** the system SHALL compute accuracy for (PT + grade) vs gold (target ≥0.80)

#### Scenario: Dose normalization accuracy

- **WHEN** evaluating dose extractions
- **THEN** the system SHALL compute UCUM correctness (target ≥0.95) and schedule field accuracy (target ≥0.90)

#### Scenario: Eligibility logic accuracy

- **WHEN** evaluating eligibility extractions
- **THEN** the system SHALL compute numeric threshold exactness (target ≥0.90) and condition/lab code mapping (target ≥0.85)
