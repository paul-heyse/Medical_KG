# Add Briefing Outputs (Topic Dossiers, Evidence Maps, Interview Kits)

## Why

The primary use case is pre-engagement knowledge readiness: analysts need comprehensive, evidence-backed understanding of medical topics (therapy areas, devices, biomarkers) before participant interviews. Automated briefing generation from KG queries synthesizes PICO, endpoints, effect sizes, safety profiles, dosing, eligibility, and guideline stances—all with citations.

## What Changes

- Implement topic dossier generator (parameterized by topic: {condition, intervention, outcome}; produces PICO synopsis, endpoint effect sheet, safety profile with AEs+MedDRA+grade, dose guidance with UCUM, eligibility snapshot, guideline stance)
- Create evidence map builder (who found what, in which population, with certainty; linked to exact source spans)
- Implement interview kit generator (auto-propose questions on unresolved evidence, subpopulation effects, long-term safety, mechanism gaps)
- Add coverage report (list included studies, labels, guidelines, known gaps)
- Implement synthesis rules (aggregate effects across studies; detect conflicts; flag heterogeneity; prioritize high-certainty evidence)
- Create templates (Markdown, HTML, JSON) with citation management
- Add real-time Q&A mode (intent-aware retrieval + extraction + synthesis on-the-fly)

## Impact

- **Affected specs**: NEW `briefing-outputs` capability
- **Affected code**: NEW `/briefing/dossiers/`, `/briefing/evidence_maps/`, `/briefing/interview_kits/`, `/briefing/templates/`
- **Dependencies**: KG (query for studies, evidence, AEs, eligibility), Retrieval (augment with spans), Extraction (ensure all assertions span-grounded)
- **Downstream**: Analysts consume dossiers; interview kits used in participant prep; evidence maps for decision support
- **Quality**: 100% of asserted facts must carry citations (doc_id, start/end offsets, quotes)
