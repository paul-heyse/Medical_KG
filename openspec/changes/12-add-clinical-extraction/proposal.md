# Add Clinical Extraction (PICO, Effects, AEs, Dose, Eligibility)

## Why

Structured extraction of PICO (Population, Intervention, Comparator, Outcome), effect measures (HR/RR/OR with CI and p-values), adverse events (MedDRA PT + grade), dosing regimens (UCUM-normalized), and eligibility constraints enables evidence synthesis, guideline generation, and trial matching. Strict JSON schemas with span-grounding ensure reproducibility and auditability.

## What Changes

- Define strict JSON schemas for each extraction type (pico.json, effects.json, ae.json, dose.json, eligibility.json) with ADDED Requirements format
- Implement LLM extractors with specialized prompts per type (temperature 0.0-0.1; max_tokens 700-900)
- Add normalizers: units → UCUM, drugs → RxCUI, outcomes → LOINC, AEs → MedDRA PT, routes → standard list (PO/IV/IM/SC)
- Implement parsers: numeric CI ("0.61–0.95" → ci_low=0.61, ci_high=0.95), p-values ("p<0.001" → ".<0.001"), dose grammar
- Create span-grounding validation (every numeric/text claim must have evidence_spans with doc_id, start, end, quote)
- Add SHACL-style pre-KG checks (UCUM valid, HR/RR/OR > 0, ci_low ≤ value ≤ ci_high, AE grade ∈ {1..5})
- Implement token budget enforcement (facets ≤120 tokens; extraction outputs variable but validated)
- Write to KG: :Evidence, :EvidenceVariable, :AdverseEvent nodes with span-grounded properties

## Impact

- **Affected specs**: NEW `clinical-extraction` capability
- **Affected code**: NEW `/llm/extractors/`, `/llm/normalizers/`, `/llm/validators/`, updates to `/kg/writers/`
- **Dependencies**: vLLM (LLM extractors), Concept Catalog (code mapping), Neo4j (write Evidence/EvidenceVariable/AE nodes)
- **Downstream**: Briefing outputs (synthesize from extractions), FHIR export (Evidence resources), KG queries
- **Quality targets**: PICO completeness ≥0.85; effect F1 ≥0.80 (relaxed); AE mapping accuracy ≥0.80; eligibility logic accuracy ≥0.85
