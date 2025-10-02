# Facet Summaries Capability

## ADDED Requirements

### Requirement: Facet Type Routing

The system SHALL detect clinical intent per chunk and route to appropriate facet generators (pico, endpoint, ae, dose, eligibility).

#### Scenario: Endpoint facet routing

- **WHEN** chunk contains effect measures (HR, RR, OR) and numeric values
- **THEN** the system SHALL route to endpoint facet generator

#### Scenario: AE facet routing

- **WHEN** chunk appears in section="adverse_reactions" or contains AE terminology
- **THEN** the system SHALL route to ae facet generator

#### Scenario: Multi-facet routing

- **WHEN** chunk contains both PICO and endpoint elements
- **THEN** the system SHALL generate both pico and endpoint facets

### Requirement: PICO Facet Generator

The system SHALL generate compact PICO summaries (≤120 tokens) with span grounding.

#### Scenario: Generate PICO facet

- **WHEN** chunk contains population, intervention, and outcome
- **THEN** the system SHALL extract compact PICO with {population, interventions[], outcomes[], timeframe, evidence_spans[]} within 120 tokens

#### Scenario: Token budget enforcement

- **WHEN** PICO facet exceeds 120 tokens
- **THEN** the system SHALL compress by abbreviating verbose text while preserving key clinical terms

#### Scenario: Evidence spans required

- **WHEN** generating any PICO facet
- **THEN** facet MUST include ≥1 evidence_span or be rejected

### Requirement: Endpoint Facet Generator

The system SHALL generate compact endpoint summaries with effect measures (≤120 tokens).

#### Scenario: Generate endpoint facet

- **WHEN** chunk contains "HR 0.68 (0.61-0.95, p=0.001)"
- **THEN** the system SHALL extract {type: "HR", value: 0.68, ci_low: 0.61, ci_high: 0.95, p: "=0.001", outcome_codes[], evidence_spans[]} within 120 tokens

#### Scenario: Outcome code attachment

- **WHEN** outcome is "cardiovascular mortality"
- **THEN** the system SHALL resolve to LOINC/SNOMED and include in outcome_codes[]

#### Scenario: Model omission for budget

- **WHEN** facet with model field exceeds 120 tokens
- **THEN** the system SHALL drop model field to fit budget

### Requirement: Adverse Event Facet Generator

The system SHALL generate compact AE summaries with MedDRA PT and grade (≤120 tokens).

#### Scenario: Generate AE facet

- **WHEN** chunk contains "Grade 3 nausea in 12/100 treatment arm patients"
- **THEN** the system SHALL extract {term: "nausea", meddra_pt: "Nausea", grade: 3, count: 12, denom: 100, arm: "treatment", evidence_spans[]} within 120 tokens

#### Scenario: Automatic MedDRA mapping

- **WHEN** generating AE facet
- **THEN** the system SHALL call resolve_meddra() and include PT with confidence

#### Scenario: Serious flag extraction

- **WHEN** text indicates "serious adverse event"
- **THEN** the system SHALL set serious=true in facet

### Requirement: Dose Facet Generator

The system SHALL generate compact dosing summaries with UCUM normalization (≤120 tokens).

#### Scenario: Generate dose facet

- **WHEN** chunk contains "Enalapril 10mg PO BID"
- **THEN** the system SHALL extract {drug_label: "Enalapril", drug_codes[], amount: 10, unit: "mg", route: "PO", frequency_per_day: 2, evidence_spans[]} within 120 tokens

#### Scenario: UCUM normalization in facets

- **WHEN** dose contains non-UCUM unit
- **THEN** the system SHALL normalize to UCUM and store in unit field

#### Scenario: SPL section tagging

- **WHEN** extracting from DailyMed SPL
- **THEN** the system SHALL include loinc_section in facet metadata

### Requirement: Token Budget Enforcement

The system SHALL strictly enforce 120-token budget for all facets using Qwen tokenizer.

#### Scenario: Count tokens

- **WHEN** facet is generated
- **THEN** the system SHALL count tokens using Qwen tokenizer (same as embedding model)

#### Scenario: Compression strategy

- **WHEN** facet exceeds 120 tokens
- **THEN** the system SHALL drop fields in priority order: notes → alternates → model → arm_sizes → compress ranges

#### Scenario: Never drop evidence_spans

- **WHEN** compressing facet
- **THEN** the system SHALL preserve evidence_spans[] even if >120 tokens (hard requirement)

#### Scenario: Validation failure

- **WHEN** facet still >120 tokens after compression
- **THEN** the system SHALL reject facet and log warning

### Requirement: Facet Storage in Neo4j

The system SHALL store facets as properties on Chunk nodes with model metadata.

#### Scenario: Store PICO facet

- **WHEN** PICO facet generated
- **THEN** the system SHALL SET Chunk.facet_pico_v1 as JSON string

#### Scenario: Store endpoint facets array

- **WHEN** multiple endpoint facets generated for chunk
- **THEN** the system SHALL SET Chunk.facet_endpoint_v1 as JSON array of strings

#### Scenario: Store facet metadata

- **WHEN** storing facets
- **THEN** the system SHALL SET Chunk.facets_model_meta={model, version, prompt_hash, ts}

### Requirement: Facet Indexing in OpenSearch

The system SHALL index facets in OpenSearch with BM25F boost for improved retrieval precision.

#### Scenario: Facet JSON field

- **WHEN** indexing chunk with facets
- **THEN** the system SHALL copy all facet JSON strings to facet_json field (text + keyword multi-field)

#### Scenario: BM25F boost

- **WHEN** configuring OpenSearch mapping
- **THEN** the system SHALL set facet_json field boost=1.6 (higher than body text)

#### Scenario: Facet type filtering

- **WHEN** indexing chunk
- **THEN** the system SHALL extract facet types and store in facet_type keyword field for filtering

#### Scenario: Facet codes extraction

- **WHEN** facets contain codes (rxcui, loinc, meddra_pt)
- **THEN** the system SHALL extract all codes and store in facet_codes[] keyword field

### Requirement: Facet Deduplication

The system SHALL deduplicate facets within documents to avoid redundancy.

#### Scenario: Endpoint deduplication key

- **WHEN** two chunks produce endpoint facets with same normalized outcome and type
- **THEN** the system SHALL deduplicate by key={outcome_norm|loinc, type, timeframe} and keep highest confidence

#### Scenario: AE deduplication key

- **WHEN** two chunks produce AE facets with same term and grade
- **THEN** the system SHALL deduplicate by key={meddra_pt|term_lower, grade, arm} and keep highest confidence

#### Scenario: Mark primary facet

- **WHEN** deduplicating
- **THEN** the system SHALL mark highest-confidence facet as is_primary=true

#### Scenario: Document-scope only

- **WHEN** deduplicating facets
- **THEN** the system SHALL deduplicate within doc_id only (allow same facet across documents)

### Requirement: Optional Facet Embeddings

The system SHALL optionally compute dense embeddings for facets to enable facet-specific dense retrieval.

#### Scenario: Compute facet embeddings

- **WHEN** EMBED_FACETS=true
- **THEN** the system SHALL embed facet JSON (minified string) via Qwen and store as Chunk.facet_embedding_qwen

#### Scenario: Skip by default

- **WHEN** EMBED_FACETS=false (default)
- **THEN** the system SHALL NOT compute facet embeddings (to save storage and compute)

#### Scenario: Separate facet index

- **WHEN** facet embeddings enabled
- **THEN** the system SHALL create OpenSearch index facets_v1 with dense_vector field

### Requirement: Facet Generation API

The system SHALL provide API endpoint for on-demand facet generation.

#### Scenario: Generate facets endpoint

- **WHEN** POST /facets/generate with {chunk_ids[]}
- **THEN** the system SHALL detect intents, generate facets, and return {facets_by_chunk{chunk_id: facets[]}}

#### Scenario: Include in chunk retrieval

- **WHEN** GET /chunks/{chunk_id}
- **THEN** response SHALL include facets{pico_v1, endpoint_v1[], ae_v1[], dose_v1[]}

#### Scenario: Filter by facet type in retrieval

- **WHEN** POST /retrieve with filter={facet_type: "endpoint"}
- **THEN** the system SHALL boost chunks with endpoint facets

### Requirement: Quality Assurance

The system SHALL validate facets against schemas and quality thresholds.

#### Scenario: Schema validation

- **WHEN** facet is generated
- **THEN** the system SHALL validate against facet.[type].v1.json schema

#### Scenario: Span verification

- **WHEN** validating facet
- **THEN** the system SHALL verify all evidence_spans have valid offsets within chunk text

#### Scenario: Unit sanity checks

- **WHEN** dose facet includes unit
- **THEN** the system SHALL verify UCUM validity or reject facet

#### Scenario: Escalation queue

- **WHEN** chunk has 3 consecutive facet generation failures
- **THEN** the system SHALL add to manual review queue

### Requirement: Monitoring Metrics

The system SHALL emit facet generation metrics for quality tracking.

#### Scenario: Generation success rate

- **WHEN** generating facets
- **THEN** the system SHALL emit facet_generation_total{type, status=success|failure}

#### Scenario: Token budget violations

- **WHEN** facet exceeds 120 tokens
- **THEN** the system SHALL emit facet_token_budget_violations_total{type}

#### Scenario: Deduplication stats

- **WHEN** deduplicating facets
- **THEN** the system SHALL emit facet_deduplication_removed_total{type, reason}
