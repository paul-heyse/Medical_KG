# Implementation Tasks

## 1. Topic Dossier Generator

- [ ] 1.1 Define topic schema (condition SNOMED/MONDO, intervention RxCUI/UDI, outcome LOINC)
- [ ] 1.2 Query KG for studies matching topic (filter by :Study/:Document ABOUT :Condition/:Drug/:Outcome)
- [ ] 1.3 Aggregate PICO (collect :EvidenceVariable nodes; deduplicate populations/interventions/outcomes)
- [ ] 1.4 Aggregate endpoints (collect :Evidence nodes; group by outcome; compute meta-analysis or list individual effects with heterogeneity I²)
- [ ] 1.5 Aggregate safety (collect :AdverseEvent nodes; group by MedDRA PT + grade; compute rates per arm)
- [ ] 1.6 Aggregate dosing (collect :Intervention nodes with :HAS_DOSE edges; identify common regimens; normalize to UCUM)
- [ ] 1.7 Aggregate eligibility (collect :EligibilityConstraint nodes; extract common age ranges, lab thresholds, conditions)
- [ ] 1.8 Query guideline stance (search :Document with source=guideline filtered by topic; extract recommendations with strength+certainty)
- [ ] 1.9 Attach citations (every claim must link to doc_id + spans_json)
- [ ] 1.10 Format as Markdown/HTML/JSON with structured sections

## 2. Evidence Map Builder

- [ ] 2.1 Query KG for all :Evidence nodes matching topic
- [ ] 2.2 For each evidence: extract {study_id, population, intervention, outcome, effect_type, value, ci, p, certainty}
- [ ] 2.3 Group by outcome → intervention → population
- [ ] 2.4 Create visual representation (table or JSON) with {who, what, where, certainty, citation}
- [ ] 2.5 Flag conflicts (same outcome+intervention but contradictory effects; e.g., HR <1 vs HR >1)
- [ ] 2.6 Flag gaps (outcomes mentioned in PICO but no evidence; populations underrepresented)

## 3. Interview Kit Generator

- [ ] 3.1 Identify gaps (outcomes with no evidence; interventions with single study; AEs mentioned but no grade)
- [ ] 3.2 Identify conflicts (heterogeneous effects; contradictory findings)
- [ ] 3.3 Identify decision points (trade-offs: efficacy vs AEs; dose titration strategies; subpopulation variations)
- [ ] 3.4 Generate question bank (template: "What is known about {outcome} in {subpopulation}? [1 study, low certainty]")
- [ ] 3.5 Prioritize questions (high-impact gaps first; conflicts second; open questions third)
- [ ] 3.6 Format as list with context (include brief summary + citations for each question)

## 4. Coverage Report

- [ ] 4.1 List included studies (NCT IDs, PMIDs, SPL setids, guideline IDs)
- [ ] 4.2 Count evidence nodes (PICO, effects, AEs, eligibility)
- [ ] 4.3 Identify known gaps (e.g., "No long-term safety data >2 years"; "No pediatric trials"; "No head-to-head vs competitor X")
- [ ] 4.4 Report data freshness (most recent study date; guideline version; catalog release)

## 5. Synthesis Rules

- [ ] 5.1 Meta-analysis (if ≥3 homogeneous studies: compute pooled effect; if heterogeneous I²>50%: list individual effects with note)
- [ ] 5.2 Conflict detection (same outcome+intervention → opposite direction or non-overlapping CIs → flag)
- [ ] 5.3 Certainty prioritization (prefer high/moderate certainty evidence; flag low/very-low)
- [ ] 5.4 Dose-response (if multiple doses: order by amount; flag trends)
- [ ] 5.5 Subpopulation stratification (if age/sex/race subgroup data: present separately)

## 6. Citation Management

- [ ] 6.1 Every assertion must link to spans_json (doc_id, start, end, quote)
- [ ] 6.2 Format citations (APA/Vancouver style; include PMID, NCT, DOI when available)
- [ ] 6.3 Inline citations in Markdown/HTML ([source_id]; hover shows quote)
- [ ] 6.4 Bibliography section (list all sources with full metadata)

## 7. Templates

- [ ] 7.1 Define Markdown template (sections: Summary, PICO, Endpoints, Safety, Dosing, Eligibility, Guidelines, Coverage, Questions)
- [ ] 7.2 Define HTML template (styled; collapsible sections; citation tooltips)
- [ ] 7.3 Define JSON template (machine-readable; all fields with citations)
- [ ] 7.4 Support export formats (PDF via pandoc; Word via pandoc; JSON for API consumers)

## 8. Real-Time Q&A Mode

- [ ] 8.1 Accept natural language query (e.g., "Does sacubitril/valsartan reduce cardiovascular mortality vs enalapril in HFrEF?")
- [ ] 8.2 Route to intent (endpoint/ae/dose/eligibility/general)
- [ ] 8.3 Run retrieval (BM25/SPLADE/Dense fusion)
- [ ] 8.4 Run extraction (effects/AEs/dose as needed)
- [ ] 8.5 Synthesize answer (aggregate evidence; detect conflicts; prioritize by certainty)
- [ ] 8.6 Return structured response (answer text + evidence[] with citations)

## 9. Quality Checks

- [ ] 9.1 Verify 100% citation coverage (every claim has ≥1 span)
- [ ] 9.2 Validate span integrity (all doc_ids exist; all offsets valid)
- [ ] 9.3 Check for hallucinations (no claims without supporting spans)
- [ ] 9.4 Measure answer utility (human eval on sample: 0 unusable / 1 partially / 2 directly actionable; target avg ≥1.6)

## 10. APIs

- [ ] 10.1 POST /briefing/dossier (body: {topic{condition, intervention, outcome}, format: md|html|json}; return: {dossier, citations[]})
- [ ] 10.2 POST /briefing/evidence-map (body: {topic}; return: {map[], conflicts[], gaps[]})
- [ ] 10.3 POST /briefing/interview-kit (body: {topic}; return: {questions[], context[]})
- [ ] 10.4 POST /briefing/coverage (body: {topic}; return: {studies[], evidence_counts{}, gaps[], freshness})
- [ ] 10.5 POST /briefing/qa (body: {query, format?}; return: {answer, evidence[], confidence})

## 11. Testing

- [ ] 11.1 Integration test (sample topic → query KG → generate dossier → verify all sections present)
- [ ] 11.2 Test citation coverage (parse dossier; verify every claim links to valid spans)
- [ ] 11.3 Test conflict detection (inject contradictory evidence → verify flagged)
- [ ] 11.4 Test gap detection (incomplete PICO → verify gaps listed)
- [ ] 11.5 Human eval (5 analysts review 10 dossiers; rate utility, accuracy, completeness)

## 12. Documentation

- [ ] 12.1 Document topic schema and how to define topics
- [ ] 12.2 Create dossier template guide (how to customize sections, citations)
- [ ] 12.3 Write user guide for interview kit generation
- [ ] 12.4 Provide example dossiers (GLP-1 for obesity; SGLT2 for HFrEF; PD-1 for melanoma)
