# Clinical Extraction Playbook

This document describes the prompts, pipeline flow, normalisation rules, and
operations runbook for the clinical extraction capability.

## Prompt Library

Prompts are managed by `PromptLibrary`. Each extraction type has a deterministic
system message and a templated user prompt. Global rules applied to every prompt
are:

1. Return valid JSON only.
2. Extract facts verbatim (no inference or paraphrasing).
3. Provide evidence spans for every field.
4. Omit fields that are not present verbatim.

### Prompt Examples

| Type | System Summary | Notes |
| ---- | --------------- | ----- |
| `pico` | Population, interventions, comparators, outcomes, timeframe | Dosing captured in interventions using UCUM units |
| `effects` | Effect measures (HR/RR/OR/MD/SMD) with CI, p-values, counts | Reject inference; maintain `model` and `time_unit_ucum` when present |
| `ae` | MedDRA PT mapping, grade, counts, arm, seriousness | Retry when MedDRA mapping ambiguous |
| `dose` | Drug label, amount, UCUM unit, route, frequency, duration | Normalise routes (PO/IV) and schedule frequency |
| `eligibility` | Inclusion/exclusion split with structured logic | Extract age, lab thresholds (LOINC+UCUM), condition codes, temporal windows |

## Pipeline Flow

1. **Chunk Routing** – `_should_extract` consults chunk sections:
   - PICO: abstract/methods/registry
   - Effects: results/outcome tables
   - AEs: safety/adverse reactions
   - Dose: dosage/arms sections
   - Eligibility: ClinicalTrials.gov eligibility blocks
2. **Extraction** – Deterministic heuristics generate draft JSON objects.
3. **Normalisation** – `normalise_extractions` parses CIs, UCUM units, routes,
   lab thresholds, MedDRA/RxNorm codes. Codes below `__confidence < 0.5` are
   dropped.
4. **Validation** – `ExtractionValidator` enforces span alignment, UCUM
   validity, ratio sanity, CTCAE grade bounds, age range order, and token
   budgets (≤120 tokens for facets, ≤2000 for full extractions). Failures are
   added to the dead-letter queue with a reason hash.
5. **Provenance** – `ExtractionEnvelope` records `{model, version, prompt_hash,
   schema_hash, ts, extracted_at, chunk_ids[]}` and `build_kg_statements`
   produces Neo4j writes linking nodes to `:ExtractionActivity`.

## Normalisation Cheat Sheet

| Concern | Action |
| ------- | ------ |
| Confidence intervals | `parse_confidence_interval` handles `a–b`, `a - b`, `(a, b)` |
| P-values | `parse_p_value` preserves `<`/`=` operators |
| Counts | `parse_count` identifies `count/denom` pairs |
| UCUM units | Upper-case and validate (MG, MG/ML, MG/KG, MMOL/L) |
| Routes | Map `oral`→`PO`, `intravenous`→`IV`, leave unknowns verbatim |
| Frequencies | Map BID/TID/QID/Q12H to numeric per-day frequency |
| Labs | `parse_lab_threshold` + `resolve_lab` produce LOINC codes |
| MedDRA | `resolve_meddra` maps terms to PT with confidence |
| Drugs | `resolve_drug` attaches RxCUI/UNII codes |
| Eligibility | Age range parser and temporal parser fill structured logic |

## Metrics

`ExtractionEvaluator` computes the following headline metrics:

- **PICO completeness** – fraction of PICO extractions containing population,
  interventions, and outcomes.
- **Effect F1 (relaxed)** – F1 score allowing ±0.01 tolerance on numeric
  comparisons.
- **AE accuracy** – strict match on term + grade.
- **Dose UCUM accuracy** – share of dosing extractions with uppercase UCUM unit.
- **Eligibility logic accuracy** – age constraint equality between prediction
  and gold.

## Runbook

| Issue | Troubleshooting | Mitigation |
| ----- | --------------- | ---------- |
| High dead-letter volume | Inspect `ExtractionValidator.dead_letter.records` for common reasons | Patch prompts/normalisers, rerun failed chunks |
| UCUM validation failures | Confirm unit is in allowed list and extraction includes amount | Extend UCUM allow-list or update regex |
| Ratio sanity failures | Verify effect text; ensure heuristic parser captured numeric sign | Adjust parser to coerce absolute values or filter bad spans |
| Low eligibility accuracy | Review chunk sections; ensure routing hits ClinicalTrials.gov sections | Extend section heuristics or add table handling |
| KG write mismatches | Examine generated `WriteStatement`s for missing IDs | Update `_node_id` seeds or payload shapes |

## Testing Strategy

- Unit tests cover parsers, validators, and error handling (`tests/extraction`).
- Integration test exercises chunk → extract → normalise → validate → KG
  pipeline (`test_clinical_extraction_service_returns_expected_payload`).
- Metrics smoke test ensures evaluator runs on self-comparison data.

