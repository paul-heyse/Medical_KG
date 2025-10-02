# Add Quality Evaluation (Test Harness, Metrics, CI Gates)

## Why

Continuous quality monitoring ensures retrieval recall, EL accuracy, extraction F1, and end-to-end faithfulness meet production thresholds. Automated evaluation harness with gold sets, CI gates, and drift detection prevents regressions and enables confident deployments.

## What Changes

- Create gold annotation sets (120 IMRaD articles, 150 ClinicalTrials studies, 100 DailyMed labels, 60 guidelines) with inter-annotator agreement κ≥0.75
- Define query sets per intent (600 endpoint, 500 AE, 400 dose, 400 eligibility, 400 PICO/context queries) with gold spans and codes
- Implement evaluation scripts: eval_chunking.py, eval_retrieval.py, eval_el.py, eval_extract.py, eval_rag.py
- Define metrics & thresholds:
  - Chunking: intra-coherence ≥0.60, boundary alignment ≥70%, no table splits
  - Retrieval: Recall@20 ≥0.85 (endpoint), ≥0.82 (AE), ≥0.85 (dose), ≥0.90 (eligibility); nDCG@10 +5 points vs BM25 only
  - EL: ID accuracy ≥0.95, concept accuracy ≥0.85, coverage ≥0.80
  - Extraction: PICO completeness ≥0.85, effect F1 ≥0.80, AE mapping ≥0.80, eligibility logic ≥0.85
  - RAG: faithfulness (span-grounding) 100%, hallucination rate ≤1%, answer utility avg ≥1.6
- Add CI/CD gates (PR must pass smoke eval; nightly full eval; release must meet all thresholds)
- Implement drift detection (weekly sentinel queries; alert if nDCG drops >3 points or overlap <0.6)
- Create dashboards (metrics trends, error analysis, per-intent breakdowns)

## Impact

- **Affected specs**: NEW `quality-evaluation` capability
- **Affected code**: NEW `/eval/`, `/eval/datasets/`, `/eval/scripts/`, `/eval/reports/`
- **Dependencies**: Gold sets (manual annotation), retrieval/extraction/KG services (for eval), CI/CD pipeline (for gates)
- **Downstream**: CI blocks merges that regress quality; nightly reports track trends; alerts trigger investigations
- **Quality assurance**: Go/No-Go release decision based on eval metrics
