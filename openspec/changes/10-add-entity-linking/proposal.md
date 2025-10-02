# Add Entity Linking (NER + EL Adjudication)

## Why

Accurate entity linking maps text mentions to canonical ontology concepts (RxCUI, SNOMED, LOINC, MedDRA), enabling semantic queries, code-based filtering, and FHIR-compliant outputs. Multi-stage pipeline (NER → candidate generation → LLM adjudication) balances recall and precision while maintaining span-level provenance.

## What Changes

- Implement NER stack: scispaCy (en_core_sci_sm/md), QuickUMLS (if licensed), regex detectors for deterministic IDs (RxCUI, UNII, NCT, LOINC, PMID, UDI-DI)
- Add custom NER heads for medical entities (drug, dose, route, frequency, lab_value, adverse_event, eligibility)
- Implement candidate generation: deterministic ID matching, dictionary (exact/fuzzy via Concept Catalog), SPLADE sparse search, dense KNN (Qwen)
- Create LLM adjudication service (function-calling schema; temperature 0.0-0.2; evidence span required)
- Implement decision rules (accept if score ≥0.70 and ID validator passes; prefer most specific in hierarchy)
- Add clinical NLP guardrails (ConText/NegEx for negation/uncertainty; section-aware filtering)
- Write to KG: create (:Chunk)-[:MENTIONS {confidence, start, end, quote}]->(:Concept) edges
- Implement review queue for low-confidence mappings (score < threshold)

## Impact

- **Affected specs**: NEW `entity-linking` capability
- **Affected code**: NEW `/llm/el_adjudicator/`, `/ontology/ner/`, updates to `/kg/writers/`
- **Dependencies**: scispaCy, QuickUMLS (optional; UMLS license), Concept Catalog (candidates), vLLM (LLM adjudication), Neo4j (write mentions)
- **Downstream**: Clinical extraction (uses linked concepts), KG queries (filter by codes), FHIR export (CodeableConcepts)
- **Quality targets**: Deterministic ID accuracy ≥0.95; concept EL accuracy ≥0.85; coverage ≥0.80
