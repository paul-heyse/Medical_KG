# Facet Generation Reference

This guide documents the facet summarisation pipeline, schemas, and operational
runbooks required by the facet summaries capability.

## Schemas

Facet payloads are stored as minified JSON. The tables below summarise the core
fields. All payloads include `token_budget=120`, `evidence_spans[]`, and
optional `confidence`.

### PICO (`facet.pico.v1.json`)

| Field | Type | Notes |
| ----- | ---- | ----- |
| `population` | string | Verbatim text describing the cohort |
| `interventions[]` | string | Distinct interventions in verbatim words |
| `comparators[]` | string | Empty if not explicitly mentioned |
| `outcomes[]` | string | Clinical outcomes mentioned verbatim |
| `timeframe` | string? | Normalised timeframe if stated |

### Endpoint (`facet.endpoint.v1.json`)

| Field | Type | Notes |
| ----- | ---- | ----- |
| `name` | string | Normalised outcome name |
| `effect_type` | enum(HR, RR, OR, MD, SMD) | Ratio values must be > 0 |
| `value`, `ci_low`, `ci_high` | float? | Parsed from text; CI bounds optional |
| `p_value` | string? | Maintains operator (e.g., `=0.01`, `<0.001`) |
| `n_total` | int? | Total population if stated |
| `arm_sizes[]` | int[]? | Trial arm sizes |
| `time_unit_ucum` | string? | UCUM code for timepoint granularity |
| `outcome_codes[]` | Code[] | LOINC/SNOMED with `__confidence` >= 0.5 |

### Adverse Event (`facet.ae.v1.json`)

| Field | Type | Notes |
| ----- | ---- | ----- |
| `term` | string | Verbatim term |
| `meddra_pt` | string? | Preferred Term resolved via `resolve_meddra()` |
| `grade` | int? | CTCAE grade 1-5 |
| `count`, `denom` | int? | Event counts/denominators |
| `arm` | string? | Trial arm label |
| `serious` | bool? | True when SAE language detected |
| `onset_days` | float? | Numeric onset timing when stated |
| `codes[]` | Code[] | MedDRA codes with `__confidence` >= 0.5 |

### Dose (`facet.dose.v1.json`)

| Field | Type | Notes |
| ----- | ---- | ----- |
| `drug_label` | string | Normalised label (RxNorm preferred) |
| `drug_codes[]` | Code[] | RxCUI/UNII with `__confidence` >= 0.5 |
| `amount` | float? | Parsed numeric amount |
| `unit` | string? | UCUM-normalised (e.g., `MG`, `MG/ML`) |
| `route` | string? | Abbreviated route (PO, IV, etc.) |
| `frequency_per_day` | float? | Converted from schedules (BID→2, QID→4) |
| `duration_days` | float? | Total duration in days |
| `loinc_section` | string? | LOINC code when sourced from SPL |

## Generation Workflow

1. **Routing** – `FacetRouter` blends intent tags, table heuristics, and
   section cues to emit zero or more facet types for each chunk.
2. **LLM prompts** – Each facet type has a deterministic prompt that enforces
   verbatim extraction, evidence spans, and the 120-token budget. Global rules
   forbid inference and demand JSON-only responses.
3. **Normalisation** – Post-processing parses confidence intervals, UCUM units,
   routes, and MedDRA/RxNorm codes. Codes with `__confidence < 0.5` are dropped.
4. **Validation** – `FacetValidator` ensures spans align with chunk text,
   enforces UCUM lists, checks ratio sanity, and re-counts tokens. Failures are
   retried up to twice before escalating to the manual-review queue.
5. **Deduplication** – Facets are deduplicated within a document using outcome
   + effect type (endpoints) or MedDRA PT + grade + arm (AEs). The retained
   facet is marked `is_primary=true`.
6. **Indexing** – Facets are written to OpenSearch (`facet_json`, `facet_type`,
   `facet_codes`) and optionally to the `facets_v1` vector index when facet
   embeddings are enabled.

## Normalisation Rules

- **Numerics** – Thousands separators are stripped, en-dash ranges parse to
  `ci_low`/`ci_high`, and `p<0.001` becomes `p_value="<0.001"`.
- **UCUM** – Units are upper-cased and validated against the allowed UCUM list;
  unsupported units raise validation errors. Composite expressions such as
  `mg/kg` are normalised.
- **Routes** – Routes normalise to abbreviations: `oral→PO`, `intravenous→IV`.
- **Coding** – Drug labels resolve to RxCUI/UNII, outcomes to LOINC/SNOMED,
  and adverse events to MedDRA PT/LLT. Codes below the confidence threshold are
  removed before indexing.
- **Token Budget** – JSON payloads must stay ≤120 tokens (Qwen tokenizer).
  Optional fields are dropped in the order notes → alternates → model →
  arm_sizes when compression is required.

## Operations Runbook

| Symptom | Checks | Remediation |
| ------- | ------ | ----------- |
| **Low facet completeness** | Inspect routing logs for missing intent tags | Tune routing heuristics or add section overrides |
| **Schema validation failures** | Review `FacetService.failure_reasons()` | Fix LLM prompt violations or extend normalisers |
| **Token budget violations** | Confirm compression priorities executed | Reduce prompt verbosity; trim optional narrative fields |
| **Unit errors** | Check validator UCUM list | Extend allowed UCUM codes or adjust resolver mappings |
| **Manual review backlog** | Inspect `FacetService.escalation_queue` | Retry with repaired prompts or flag for annotator triage |

## Prompt Tuning Tips

- Keep demonstrations concise (<60 tokens) and grounded in real SPL/CTGov
  snippets.
- Reinforce evidence-span requirements with explicit failure modes in the
  system prompt (e.g., “omit fields lacking verbatim support”).
- When the LLM emits incorrect structures, supply the validator error message
  as feedback on the repair attempt; the retry loop honours two retries.

