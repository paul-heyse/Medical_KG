# Quality Evaluation Capability

## ADDED Requirements

### Requirement: Gold Annotation Sets

The system SHALL curate gold annotation sets with inter-annotator agreement κ≥0.75 for evaluation.

#### Scenario: Curate IMRaD articles

- **WHEN** building gold set
- **THEN** the system SHALL curate 120 IMRaD articles (40 cardiology, 40 oncology, 40 infectious disease) from PMC OA

#### Scenario: Curate clinical trials

- **WHEN** building gold set
- **THEN** the system SHALL curate 150 ClinicalTrials.gov studies stratified by phase 2/3 and intervention type

#### Scenario: Annotate with inter-annotator agreement

- **WHEN** annotating documents
- **THEN** two independent annotators + adjudicator SHALL annotate PICO, endpoints, AEs, dosing, eligibility with Cohen's κ (target ≥0.75 overall, ≥0.8 categorical fields)

#### Scenario: Store gold with spans

- **WHEN** finalizing gold annotations
- **THEN** the system SHALL store in versioned JSONL with spans {doc_id, start, end, quote}

### Requirement: Query Sets

The system SHALL define query sets per intent with gold relevance judgments.

#### Scenario: Endpoint queries

- **WHEN** creating endpoint query set
- **THEN** the system SHALL define 600 queries like "HR for {outcome} with {drug} in {population}" with gold doc_ids and spans

#### Scenario: Adverse event queries

- **WHEN** creating AE query set
- **THEN** the system SHALL define 500 queries about grade, incidence, and specific AE terms

#### Scenario: Link to gold docs

- **WHEN** defining queries
- **THEN** each query SHALL link to gold doc IDs, relevance scores (0-3), and expected spans

### Requirement: Chunking Evaluation

The system SHALL compute intra/inter coherence, boundary alignment, and size distribution.

#### Scenario: Compute intra-coherence

- **WHEN** evaluating chunking
- **THEN** the system SHALL compute mean sentence-to-sentence coherence within chunks (target ≥0.60)

#### Scenario: Compute boundary alignment

- **WHEN** documents have section boundaries
- **THEN** the system SHALL compute fraction of chunk boundaries aligned with sections (target ≥70%)

#### Scenario: Size distribution analysis

- **WHEN** evaluating chunks
- **THEN** the system SHALL report mean, std, min, max token counts and verify within target ± 100 tokens

### Requirement: Retrieval Evaluation

The system SHALL compute Recall@K, nDCG@K, MRR per intent with fusion vs individual retrievers.

#### Scenario: Compute Recall@20

- **WHEN** evaluating retrieval
- **THEN** the system SHALL compute Recall@20 per intent (targets: endpoint ≥0.85, AE ≥0.82, dose ≥0.85, eligibility ≥0.90)

#### Scenario: Compute nDCG@10

- **WHEN** evaluating ranking
- **THEN** the system SHALL compute nDCG@10 and verify fusion is +5 points vs BM25-only

#### Scenario: Component analysis

- **WHEN** analyzing retrievers
- **THEN** the system SHALL create Venn diagrams showing BM25/SPLADE/Dense overlap and identify recall gaps

### Requirement: Entity Linking Evaluation

The system SHALL compute ID accuracy, concept accuracy, coverage, and calibration.

#### Scenario: ID accuracy

- **WHEN** evaluating deterministic IDs
- **THEN** the system SHALL compute accuracy for RxCUI, UNII, LOINC, NCT, UDI vs gold (target ≥0.95)

#### Scenario: Concept EL accuracy

- **WHEN** evaluating concept mappings
- **THEN** the system SHALL compute micro-averaged accuracy vs gold UMLS/SNOMED/LOINC (target ≥0.85)

#### Scenario: Coverage

- **WHEN** measuring linked mentions
- **THEN** the system SHALL compute fraction with confidence ≥ threshold (target ≥0.80)

#### Scenario: Calibration

- **WHEN** assessing confidence scores
- **THEN** the system SHALL compute reliability diagram and ECE (target ≤0.05 at threshold 0.70)

### Requirement: Extraction Evaluation

The system SHALL compute PICO completeness, effect F1, AE accuracy, dose/eligibility accuracy.

#### Scenario: PICO completeness

- **WHEN** evaluating PICO extractions
- **THEN** the system SHALL compute fraction with all {population, interventions, outcomes} present (target ≥0.85)

#### Scenario: Effect F1 scores

- **WHEN** evaluating effects
- **THEN** the system SHALL compute exact F1 (all fields match) and relaxed F1 (abs error ≤0.01) with target ≥0.80 relaxed

#### Scenario: AE mapping accuracy

- **WHEN** evaluating AEs
- **THEN** the system SHALL compute accuracy for (PT + grade) vs gold (target ≥0.80)

#### Scenario: Dose normalization

- **WHEN** evaluating dosing
- **THEN** the system SHALL compute UCUM correctness (target ≥0.95) and schedule field accuracy (target ≥0.90)

### Requirement: RAG Faithfulness Evaluation

The system SHALL verify 100% span-grounding and measure hallucination rate.

#### Scenario: Faithfulness rate

- **WHEN** evaluating briefing outputs
- **THEN** the system SHALL verify every claim has ≥1 valid span (target 100%)

#### Scenario: Hallucination detection

- **WHEN** checking for unsupported claims
- **THEN** the system SHALL compute hallucination rate (claims without spans; target ≤1%)

#### Scenario: Answer utility

- **WHEN** evaluating Q&A
- **THEN** human evaluators SHALL rate 10 dossiers/month on 0-2 scale (target avg ≥1.6)

### Requirement: CI/CD Evaluation Gates

The system SHALL enforce evaluation gates in CI/CD preventing regressions.

#### Scenario: PR smoke eval

- **WHEN** pull request opened
- **THEN** CI SHALL run eval on 10 docs per family and block merge if smoke eval fails

#### Scenario: Nightly full eval

- **WHEN** nightly cron triggers
- **THEN** CI SHALL run full eval on all datasets, publish report, alert on failures

#### Scenario: Release gate

- **WHEN** releasing to production
- **THEN** all metrics MUST meet thresholds on frozen test set + sign-off checklist

### Requirement: Drift Detection

The system SHALL run weekly sentinel queries and alert on nDCG drops or overlap changes.

#### Scenario: Sentinel queries

- **WHEN** drift detection runs
- **THEN** the system SHALL execute 50 stable queries per intent and compare nDCG@10 vs last week

#### Scenario: nDCG drop alert

- **WHEN** nDCG drops >3 points
- **THEN** the system SHALL alert ops team with drill-down link

#### Scenario: Overlap change alert

- **WHEN** Jaccard overlap of top-20 results < 0.6
- **THEN** the system SHALL alert potential retrieval drift

### Requirement: Evaluation Scripts

The system SHALL provide eval scripts for each capability with JSON+HTML reports.

#### Scenario: eval_retrieval.py

- **WHEN** running `python eval/eval_retrieval.py --dataset endpoint`
- **THEN** the system SHALL compute Recall@K, nDCG@K, MRR and output report.json + report.html

#### Scenario: eval_el.py

- **WHEN** running `python eval/eval_el.py`
- **THEN** the system SHALL compute ID accuracy, concept accuracy, coverage, calibration and output report

#### Scenario: eval_extract.py

- **WHEN** running `python eval/eval_extract.py --type pico`
- **THEN** the system SHALL compute completeness, F1, accuracy and output report

### Requirement: Dashboards and Trends

The system SHALL provide Grafana dashboards showing metrics trends over time.

#### Scenario: Metrics trends dashboard

- **WHEN** viewing evaluation dashboard
- **THEN** Grafana SHALL show Recall@20, nDCG@10, EL accuracy, extraction F1 over time (daily/weekly)

#### Scenario: Per-intent breakdown

- **WHEN** drilling into retrieval metrics
- **THEN** dashboard SHALL show metrics by intent (endpoint, AE, dose, eligibility, PICO, general)

#### Scenario: Error analysis

- **WHEN** reviewing failures
- **THEN** dashboard SHALL show top failed queries, common failure modes, error types

### Requirement: Data Splits and Versioning

The system SHALL maintain train/dev/test splits with frozen test set and version tracking.

#### Scenario: 70/15/15 split

- **WHEN** creating dataset splits
- **THEN** the system SHALL split gold sets: 70% train, 15% dev, 15% test

#### Scenario: Freeze test set

- **WHEN** finalizing test set
- **THEN** test set SHALL be frozen (never used for tuning) and only evaluated at release

#### Scenario: Version datasets

- **WHEN** updating gold annotations
- **THEN** the system SHALL version via git LFS or DVC and track changes
