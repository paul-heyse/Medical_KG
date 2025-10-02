# Implementation Tasks

## 1. Gold Annotation Sets

- [x] 1.1 Curate 120 IMRaD articles (40 cardiology, 40 oncology, 40 infectious disease) from PMC OA
- [x] 1.2 Curate 150 ClinicalTrials.gov studies (stratify by phase 2/3, drug/device/biologic)
- [x] 1.3 Curate 100 DailyMed SPL labels (brand/generic variety)
- [x] 1.4 Curate 60 guideline recommendation units (WHO, CDC, NICE where allowed)
- [x] 1.5 Annotate PICO, endpoints, effect sizes, AEs, dosing, eligibility with char offsets
- [x] 1.6 Two independent annotators + adjudicator; compute Cohen's κ (target ≥0.75 overall, ≥0.8 on categorical fields)
- [x] 1.7 Store gold in versioned JSONL with spans (doc_id, start, end, quote)

## 2. Query Sets

- [x] 2.1 Create 600 endpoint queries ("HR for {outcome} with {drug} in {population}")
- [x] 2.2 Create 500 AE queries ("Grade ≥3 {PT} with {drug}")
- [x] 2.3 Create 400 dose queries ("Recommended {drug} {route} dosing in {population}")
- [x] 2.4 Create 400 eligibility queries ("Inclusion criteria age range for {condition} trials")
- [x] 2.5 Create 400 PICO/context queries
- [x] 2.6 Link each query to gold doc IDs, gold spans, gold codes

## 3. Evaluation Scripts

- [x] 3.1 eval_chunking.py (compute intra/inter coherence, boundary alignment, size distribution)
- [x] 3.2 eval_retrieval.py (Recall@K, nDCG@K, MRR per intent; fusion vs individual retrievers)
- [x] 3.3 eval_el.py (ID accuracy, concept accuracy, coverage, calibration ECE)
- [x] 3.4 eval_extract.py (PICO completeness, effect F1 exact/relaxed, AE mapping, dose/eligibility accuracy)
- [x] 3.5 eval_rag.py (faithfulness rate, hallucination detection, answer utility human eval)
- [x] 3.6 Common utilities (gold loading, metric computation, report generation JSON+HTML)

## 4. Metrics & Thresholds

- [x] 4.1 Define all metrics (see proposal for list)
- [x] 4.2 Set CI gate thresholds (dev split; allow ±2 point regression)
- [x] 4.3 Set nightly threshold (full test; must meet all targets)
- [x] 4.4 Set release thresholds (frozen test set; all targets + no regressions >2 points)

## 5. CI/CD Integration

- [x] 5.1 PR gate: run eval smoke test (10 docs per family; must pass)
- [x] 5.2 Nightly cron: run full eval (all datasets; publish report; alert on failures)
- [x] 5.3 Release gate: run full eval on frozen test set; require sign-off checklist
- [x] 5.4 Block merge if smoke eval fails or introduces lint/schema errors

## 6. Drift Detection

- [x] 6.1 Define sentinel query set (50 stable queries per intent; gold answers frozen)
- [x] 6.2 Run weekly (compare nDCG@10 vs last week; alert if drop >3 points)
- [x] 6.3 Compute Jaccard overlap of top-20 results (alert if <0.6)
- [x] 6.4 Track EL acceptance rate monthly (alert if <0.80)
- [x] 6.5 Track extraction quality monthly (alert if PICO completeness <0.85)

## 7. Error Analysis & Dashboards

- [x] 7.1 Grafana dashboard: metrics trends (Recall@20, nDCG@10, EL accuracy, extraction F1 over time)
- [x] 7.2 Grafana dashboard: per-intent breakdowns (retrieval metrics by intent)
- [x] 7.3 Grafana dashboard: error types (no spans, schema violations, SHACL failures)
- [x] 7.4 Error analysis reports (top failed queries; common failure modes; drill-down by doc/chunk)
- [x] 7.5 Venn diagrams (BM25/SPLADE/Dense overlap; identify recall gaps)

## 8. Data Splits

- [x] 8.1 Split gold sets: 70/15/15 train/dev/test
- [x] 8.2 Freeze test set (never used for tuning; only for release eval)
- [x] 8.3 Version datasets (git LFS or DVC; track changes)

## 9. Reproducibility

- [x] 9.1 Fix random seeds (chunking coherence, retrieval, extractors)
- [x] 9.2 Version model weights (embeddings, SPLADE, LLM extractors)
- [x] 9.3 Store eval run metadata (config_version, model_versions, timestamp)
- [x] 9.4 Archive reports (eval/reports/YYYY-MM-DD/{metrics.json, report.html})

## 10. Human Evaluation

- [x] 10.1 RAG answer utility: 5 analysts review 10 dossiers/month; rate 0-2 (target avg ≥1.6)
- [x] 10.2 Extraction quality spot-check: review 5% of low-confidence extractions
- [x] 10.3 EL review queue: clear critical items within 5 business days
- [x] 10.4 Collect feedback; update gold sets quarterly

## 11. Load & Performance Testing

- [x] 11.1 Scenarios: burst 50 QPS for 2 min; steady 10 QPS for 1 hour
- [x] 11.2 Mixed intents (endpoint 40%, AE 25%, dose 15%, eligibility 10%, others 10%)
- [x] 11.3 Measure P50/P95/P99 latency per endpoint
- [x] 11.4 Flamegraphs per stage (BM25, SPLADE, ANN, reranker)
- [x] 11.5 Back-pressure handling (if P95 > SLO → disable reranker, reduce topK, switch to RRF)

## 12. Testing

- [x] 12.1 Unit tests for metric computation (mock predictions vs gold → verify Recall, nDCG, F1)
- [x] 12.2 Integration test (run eval scripts on sample data; verify reports generated)
- [x] 12.3 Test CI gate (simulate regression → verify PR blocked)
- [x] 12.4 Test drift detection (inject nDCG drop → verify alert triggered)

## 13. Documentation

- [x] 13.1 Document gold set curation process (annotation guidelines, IAA targets)
- [x] 13.2 Create eval harness user guide (run locally, interpret reports)
- [x] 13.3 Document metrics definitions and thresholds
- [x] 13.4 Write runbook for quality regressions (investigate, fix, re-eval)
