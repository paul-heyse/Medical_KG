# Entity Linking Capability

## ADDED Requirements

### Requirement: Named Entity Recognition Stack

The system SHALL provide multi-model NER stack including scispaCy, QuickUMLS (if licensed), and deterministic regex detectors for medical entities.

#### Scenario: scispaCy NER

- **WHEN** processing chunk text
- **THEN** the system SHALL apply en_core_sci_md model and extract entities with types: DISEASE, CHEMICAL, GENE_OR_GENE_PRODUCT

#### Scenario: Custom NER heads

- **WHEN** running specialized taggers
- **THEN** the system SHALL extract custom types: drug, dose, route, frequency, lab_value, adverse_event, eligibility, outcome with span offsets

#### Scenario: QuickUMLS matching

- **WHEN** UMLS licensed and QuickUMLS enabled
- **THEN** the system SHALL match spans to UMLS CUIs using Jaccard similarity (threshold=0.7) with stemming and window size ≤6 tokens

### Requirement: Deterministic ID Detectors

The system SHALL extract and validate deterministic identifiers using regex patterns and checksum validation.

#### Scenario: RxCUI detection

- **WHEN** text contains numeric RxCUI (e.g., "RxCUI: 123456" or standalone "123456" in drug context)
- **THEN** the system SHALL extract RxCUI and create candidate with score=1.0

#### Scenario: UNII detection

- **WHEN** text contains 10-character alphanumeric UNII code
- **THEN** the system SHALL validate format [A-Z0-9]{10} and create candidate with deterministic=true

#### Scenario: LOINC detection

- **WHEN** text contains pattern \d{1,7}-\d
- **THEN** the system SHALL validate as LOINC code and link to Concept Catalog

#### Scenario: NCT ID detection

- **WHEN** text contains NCT\d{8}
- **THEN** the system SHALL extract trial identifier and verify format

#### Scenario: UDI-DI validation

- **WHEN** text contains 14-digit GTIN
- **THEN** the system SHALL validate mod-10 checksum and extract device identifier

### Requirement: Candidate Generation Pipeline

The system SHALL generate entity linking candidates using dictionary lookup, SPLADE sparse search, and dense KNN search.

#### Scenario: Dictionary exact match

- **WHEN** mention="enalapril maleate"
- **THEN** the system SHALL query OpenSearch concepts_v1 with multi_match on label^2, synonyms and return top-20 with BM25 scores

#### Scenario: Dictionary fuzzy match

- **WHEN** mention="diabetis" (typo)
- **THEN** the system SHALL apply fuzzy search (Levenshtein distance ≤2) and return matching concepts with lower scores

#### Scenario: SPLADE sparse search

- **WHEN** mention="chest discomfort"
- **THEN** the system SHALL expand via SPLADE, search splade_terms field in concepts_v1, and return top-20 with BM25F scores

#### Scenario: Dense KNN search

- **WHEN** mention="elevated blood sugar" with context="patient with obesity"
- **THEN** the system SHALL embed mention + context via Qwen, search Neo4j concept_qwen_idx, and return top-20 with cosine similarity

#### Scenario: Candidate aggregation via RRF

- **WHEN** all three retrieval modalities complete
- **THEN** the system SHALL aggregate candidates using RRF (k=60) and return top-20 final candidates with scores

### Requirement: LLM Adjudication Service

The system SHALL use LLM function-calling to adjudicate entity linking with span-grounded evidence.

#### Scenario: Adjudication prompt

- **WHEN** invoking LLM for adjudication
- **THEN** the system SHALL provide mention, context, candidates[], and prompt: "You are a medical entity linker. Choose the best matching concept or return null if ambiguous. Provide evidence span from context."

#### Scenario: JSON schema enforcement

- **WHEN** LLM returns response
- **THEN** the system SHALL validate against el_adjudicator.schema.json requiring: {chosen_id, ontology, score 0-1, evidence_span{start, end, quote}, alternates[], notes}

#### Scenario: Temperature control

- **WHEN** calling LLM
- **THEN** the system SHALL use temperature=0.0-0.2 and max_tokens=600 for deterministic outputs

#### Scenario: Retry on invalid JSON

- **WHEN** LLM returns malformed JSON
- **THEN** the system SHALL retry with error feedback (max 2 retries) and provide repair instructions

### Requirement: Decision Rules and Post-Processing

The system SHALL apply decision rules to accept/reject/queue entity linking results based on confidence and validation.

#### Scenario: High confidence acceptance

- **WHEN** LLM returns score ≥0.70 AND (if ID present) validator passes
- **THEN** the system SHALL accept mapping and create MENTIONS edge

#### Scenario: Deterministic ID precedence

- **WHEN** both deterministic ID (RxCUI, UNII, LOINC) and concept candidates available
- **THEN** the system SHALL prefer deterministic ID if validator passes

#### Scenario: Hierarchy specificity

- **WHEN** multiple accepted concepts from same ontology
- **THEN** the system SHALL choose most specific (deepest in IS_A hierarchy)

#### Scenario: Low confidence queue

- **WHEN** score < 0.70 or conflicting candidates
- **THEN** the system SHALL add to review_queue with top-5 alternates and reason

### Requirement: Clinical NLP Guardrails

The system SHALL apply ConText/NegEx for negation and uncertainty detection with section-aware boosting.

#### Scenario: Negation detection

- **WHEN** mention preceded by negation trigger ("no", "denies", "without", "absent")
- **THEN** the system SHALL tag MENTIONS edge with negated=true

#### Scenario: Uncertainty detection

- **WHEN** mention preceded by uncertainty marker ("possible", "probable", "suspected")
- **THEN** the system SHALL tag MENTIONS edge with hypothetical=true

#### Scenario: Section-aware boosting

- **WHEN** mention type="adverse_event" appears in section="adverse_reactions"
- **THEN** the system SHALL boost candidate confidence by 0.1 (cap at 1.0)

#### Scenario: Co-reference resolution

- **WHEN** mention="the study drug" in same chunk as intervention mention
- **THEN** the system SHALL resolve to intervention concept and link accordingly

### Requirement: Span Cleanup and Expansion

The system SHALL expand entity spans to include adjacent units and collapse overlapping matches.

#### Scenario: Unit expansion

- **WHEN** mention="10" adjacent to "mg"
- **THEN** the system SHALL expand span to "10 mg" and update offsets

#### Scenario: Overlap resolution

- **WHEN** "enalapril maleate" and "enalapril" both detected with overlapping spans
- **THEN** the system SHALL keep most specific match ("enalapril maleate") if both backed by valid concepts

#### Scenario: Span validation

- **WHEN** creating mention
- **THEN** the system SHALL verify start < end and offsets within chunk.text length

### Requirement: Write to Knowledge Graph

The system SHALL create MENTIONS edges linking chunks to concepts with confidence and provenance.

#### Scenario: Create MENTIONS edge

- **WHEN** entity linking accepts mapping
- **THEN** the system SHALL CREATE (:Chunk)-[:MENTIONS {confidence, start, end, quote, negated?, hypothetical?}]->(:Concept)

#### Scenario: Create identifier edges

- **WHEN** deterministic ID detected
- **THEN** the system SHALL CREATE (:Chunk)-[:HAS_IDENTIFIER]->(:Identifier {scheme, code})

#### Scenario: Link to extraction activity

- **WHEN** writing mentions
- **THEN** the system SHALL link to :ExtractionActivity (model, version, timestamp) via :WAS_GENERATED_BY

#### Scenario: Batch writes

- **WHEN** linking entities for document
- **THEN** the system SHALL batch writes (1000 edges/tx) via APOC for performance

### Requirement: Review Queue

The system SHALL maintain review queue for low-confidence and conflicting mappings with UI requirements.

#### Scenario: Queue entry creation

- **WHEN** mapping confidence < 0.70
- **THEN** the system SHALL INSERT into review_queue (mention_id, chunk_id, text, candidates[], reason, status=pending)

#### Scenario: UI requirements

- **WHEN** reviewer accesses queue
- **THEN** UI SHALL display PDF with span highlights, mention context ±2 sentences, top-5 candidates with scores, one-click accept/correct/reject buttons

#### Scenario: Manual correction storage

- **WHEN** reviewer corrects mapping
- **THEN** the system SHALL create :SAME_AS edge with evidence="manual" and store in curated crosswalks for future training

#### Scenario: SLA tracking

- **WHEN** item enters queue
- **THEN** the system SHALL track age and alert if critical items (deterministic ID conflicts) exceed 5 business days

### Requirement: Evaluation Metrics

The system SHALL compute and track entity linking quality metrics.

#### Scenario: ID accuracy

- **WHEN** comparing against gold annotations
- **THEN** the system SHALL compute accuracy for deterministic IDs (RxCUI, UNII, LOINC, NCT, UDI) with target ≥0.95

#### Scenario: Concept EL accuracy

- **WHEN** evaluating concept mappings
- **THEN** the system SHALL compute micro-averaged accuracy vs gold UMLS/SNOMED/LOINC with target ≥0.85

#### Scenario: Coverage

- **WHEN** measuring linked mentions
- **THEN** the system SHALL compute fraction of mentions with confidence ≥ threshold (target ≥0.80)

#### Scenario: Calibration

- **WHEN** assessing confidence scores
- **THEN** the system SHALL compute reliability diagram and expected calibration error (target ECE ≤0.05 at threshold 0.70)

#### Scenario: Abstention rate

- **WHEN** monitoring queue
- **THEN** the system SHALL track fraction with score < threshold (target ≤0.15)
