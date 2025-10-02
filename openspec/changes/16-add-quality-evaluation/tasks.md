# Implementation Tasks

## 1. Gold Annotation Sets

- [ ] 1.1 Curate 120 IMRaD articles (40 cardiology, 40 oncology, 40 infectious disease) from PMC OA
- [ ] 1.2 Curate 150 ClinicalTrials.gov studies (stratify by phase 2/3, drug/device/biologic)
- [ ] 1.3 Curate 100 DailyMed SPL labels (brand/generic variety)
- [ ] 1.4 Curate 60 guideline recommendation units (WHO, CDC, NICE where allowed)
- [ ] 1.5 Annotate PICO, endpoints, effect sizes, AEs, dosing, eligibility with char offsets
- [ ] 1.6 Two independent annotators + adjudicator; compute Cohen's κ (target ≥0.75 overall, ≥0.8 on categorical fields)
- [ ] 1.7 Store gold in versioned JSONL with spans (doc_id, start, end, quote)

## 2. Query Sets

- [ ] 2.1 Create 600 endpoint queries ("HR for {outcome} with {drug} in {population}")
- [ ] 2.2 Create 500 AE queries ("Grade ≥3 {PT} with {drug}")
- [ ] 2.3 Create 400 dose queries ("Recommended {drug} {route} dosing in {population}")
- [ ] 2.4 Create 400 eligibility queries ("Inclusion criteria age range for {condition} trials")
- [ ] 2.5 Create 400 PICO/context queries
- [ ] 2.6 Link each query to gold doc IDs, gold spans, gold codes

## 3. Evaluation Scripts

- [ ] 3.1 eval_chunking.py (compute intra/inter coherence, boundary alignment, size distribution)
- [ ] 3.2 eval_retrieval.py (Recall@K, nDCG@K, MRR per intent; fusion vs individual retrievers)
- [ ] 3.3 eval_el.py (ID accuracy, concept accuracy, coverage, calibration ECE)
- [ ] 3.4 eval_extract.py (PICO completeness, effect F1 exact/relaxed, AE mapping, dose/eligibility accuracy)
- [ ] 3.5 eval_rag.py (faithfulness rate, hallucination detection, answer utility human eval)
- [ ] 3.6 Common utilities (gold loading, metric computation, report generation JSON+HTML)

## 4. Metrics & Thresholds

- [ ] 4.1 Define all metrics (see proposal for list)
- [ ] 4.2 Set CI gate thresholds (dev split; allow ±2 point regression)
- [ ] 4.3 Set nightly threshold (full test; must meet all targets)
- [ ] 4.4 Set release thresholds (frozen test set; all targets + no regressions >2 points)

## 5. CI/CD Integration

- [ ] 5.1 PR gate: run eval smoke test (10 docs per family; must pass)
- [ ] 5.2 Nightly cron: run full eval (all datasets; publish report; alert on failures)
- [ ] 5.3 Release gate: run full eval on frozen test set; require sign-off checklist
- [ ] 5.4 Block merge if smoke eval fails or introduces lint/schema errors

## 6. Drift Detection

- [ ] 6.1 Define sentinel query set (50 stable queries per intent; gold answers frozen)
- [ ] 6.2 Run weekly (compare nDCG@10 vs last week; alert if drop >3 points)
- [ ] 6.3 Compute Jaccard overlap of top-20 results (alert if <0.6)
- [ ] 6.4 Track EL acceptance rate monthly (alert if <0.80)
- [ ] 6.5 Track extraction quality monthly (alert if PICO completeness <0.85)

## 7. Error Analysis & Dashboards

- [ ] 7.1 Grafana dashboard: metrics trends (Recall@20, nDCG@10, EL accuracy, extraction F1 over time)
- [ ] 7.2 Grafana dashboard: per-intent breakdowns (retrieval metrics by intent)
- [ ] 7.3 Grafana dashboard: error types (no spans, schema violations, SHACL failures)
- [ ] 7.4 Error analysis reports (top failed queries; common failure modes; drill-down by doc/chunk)
- [ ] 7.5 Venn diagrams (BM25/SPLADE/Dense overlap; identify recall gaps)

## 8. Data Splits

- [ ] 8.1 Split gold sets: 70/15/15 train/dev/test
- [ ] 8.2 Freeze test set (never used for tuning; only for release eval)
- [ ] 8.3 Version datasets (git LFS or DVC; track changes)

## 9. Reproducibility

- [ ] 9.1 Fix random seeds (chunking coherence, retrieval, extractors)
- [ ] 9.2 Version model weights (embeddings, SPLADE, LLM extractors)
- [ ] 9.3 Store eval run metadata (config_version, model_versions, timestamp)
- [ ] 9.4 Archive reports (eval/reports/YYYY-MM-DD/{metrics.json, report.html})

## 10. Human Evaluation

- [ ] 10.1 RAG answer utility: 5 analysts review 10 dossiers/month; rate 0-2 (target avg ≥1.6)
- [ ] 10.2 Extraction quality spot-check: review 5% of low-confidence extractions
- [ ] 10.3 EL review queue: clear critical items within 5 business days
- [ ] 10.4 Collect feedback; update gold sets quarterly

## 11. Load & Performance Testing

- [ ] 11.1 Scenarios: burst 50 QPS for 2 min; steady 10 QPS for 1 hour
- [ ] 11.2 Mixed intents (endpoint 40%, AE 25%, dose 15%, eligibility 10%, others 10%)
- [ ] 11.3 Measure P50/P95/P99 latency per endpoint
- [ ] 11.4 Flamegraphs per stage (BM25, SPLADE, ANN, reranker)
- [ ] 11.5 Back-pressure handling (if P95 > SLO → disable reranker, reduce topK, switch to RRF)

## 12. Testing

- [ ] 12.1 Unit tests for metric computation (mock predictions vs gold → verify Recall, nDCG, F1)
- [ ] 12.2 Integration test (run eval scripts on sample data; verify reports generated)
- [ ] 12.3 Test CI gate (simulate regression → verify PR blocked)
- [ ] 12.4 Test drift detection (inject nDCG drop → verify alert triggered)

## 13. Documentation

- [ ] 13.1 Document gold set curation process (annotation guidelines, IAA targets)
- [ ] 13.2 Create eval harness user guide (run locally, interpret reports)
- [ ] 13.3 Document metrics definitions and thresholds
- [ ] 13.4 Write runbook for quality regressions (investigate, fix, re-eval)
