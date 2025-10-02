# Semantic Chunking Capability

## ADDED Requirements

### Requirement: Medical-Aware Chunking

The system SHALL chunk documents using medical domain knowledge with profile-specific strategies for IMRaD articles, clinical trials, drug labels, and guidelines.

#### Scenario: IMRaD article chunking

- **WHEN** processing document with section="introduction|methods|results|discussion"
- **THEN** the system SHALL use IMRaD profile (target_tokens=400, overlap=75, tau_coh=0.15) and prefer section boundaries

#### Scenario: Clinical trial registry chunking

- **WHEN** processing ClinicalTrials.gov study
- **THEN** the system SHALL use Registry profile (target_tokens=350, overlap=50) and chunk by structured fields (Eligibility, Arms, Outcomes, Adverse Events)

#### Scenario: Drug label chunking

- **WHEN** processing SPL with LOINC sections
- **THEN** the system SHALL use SPL profile (target_tokens=450, overlap=100, respect LOINC boundaries) and never split tables

### Requirement: Clinical Intent Tagger

The system SHALL assign clinical intent tags to sentences for routing to specialized chunking and extraction.

#### Scenario: PICO tagging

- **WHEN** sentence contains population descriptors (e.g., "patients with", "adults aged")
- **THEN** the system SHALL tag as intent="pico" using clinical_tagger model

#### Scenario: Endpoint tagging

- **WHEN** sentence contains effect measures (HR, RR, OR, p-value, CI)
- **THEN** the system SHALL tag as intent="endpoint" with confidence score

#### Scenario: Adverse event tagging

- **WHEN** sentence appears in section="adverse_reactions" or contains AE terminology
- **THEN** the system SHALL tag as intent="ae" and boost for facet generation

### Requirement: Coherence-Based Boundaries

The system SHALL compute semantic coherence between sentences and create chunk boundaries where coherence drops below threshold.

#### Scenario: Coherence calculation

- **WHEN** analyzing consecutive sentences
- **THEN** the system SHALL compute cosine similarity using sentence embeddings (MiniLM or BioSentVec) and store as coherence score

#### Scenario: Boundary detection

- **WHEN** coherence(sent_i, sent_i+1) < tau_coh (default 0.15)
- **THEN** the system SHALL create chunk boundary if current chunk ≥ min_tokens (200)

#### Scenario: Forced boundary at max tokens

- **WHEN** current chunk reaches target_tokens * 1.5
- **THEN** the system SHALL create boundary at next sentence regardless of coherence

### Requirement: Overlap Strategy

The system SHALL create overlapping chunks to preserve context at boundaries and support neighbor merging in retrieval.

#### Scenario: Overlap window

- **WHEN** creating new chunk after boundary
- **THEN** the system SHALL include last N tokens from previous chunk where N = overlap parameter (default 75 tokens)

#### Scenario: Overlap span tracking

- **WHEN** chunks overlap
- **THEN** the system SHALL record overlap_with_prev{chunk_id, start, end} to support deduplication

#### Scenario: No overlap at section boundaries

- **WHEN** boundary coincides with IMRaD section change or LOINC section boundary
- **THEN** the system SHALL NOT create overlap (respect hard boundaries)

### Requirement: Table Handling

The system SHALL never split tables across chunks and SHALL preserve table structure with captions.

#### Scenario: Table as standalone chunk

- **WHEN** table size < max_table_tokens (600)
- **THEN** the system SHALL create dedicated chunk containing table + caption + optional context sentence

#### Scenario: Large table splitting

- **WHEN** table > max_table_tokens
- **THEN** the system SHALL split by rows while preserving headers and creating logical sub-tables

#### Scenario: Table context

- **WHEN** table chunk is created
- **THEN** the system SHALL include preceding sentence (if <50 tokens) as context

### Requirement: Chunk Metadata

The system SHALL attach comprehensive metadata to each chunk for routing, retrieval, and provenance.

#### Scenario: Clinical intent metadata

- **WHEN** chunk is created
- **THEN** the system SHALL set chunk.intent using majority vote of sentence intent tags

#### Scenario: Section metadata

- **WHEN** chunk falls within IMRaD section or LOINC section
- **THEN** the system SHALL set chunk.section and chunk.section_loinc if applicable

#### Scenario: Source document linkage

- **WHEN** creating chunk
- **THEN** the system SHALL set chunk.doc_id, chunk.start_offset, chunk.end_offset mapping to Document.text canonical offsets

### Requirement: Chunk ID Generation

The system SHALL generate stable, deterministic chunk IDs based on content and position.

#### Scenario: Chunk ID format

- **WHEN** creating chunk
- **THEN** the system SHALL generate chunk_id as `{doc_id}:c{chunk_index}#{hash8}` where hash8 is first 8 chars of SHA256(chunk_text)

#### Scenario: Idempotent chunking

- **WHEN** re-chunking same document with same profile
- **THEN** the system SHALL generate identical chunk_ids for unchanged content

#### Scenario: Hash collision handling

- **WHEN** two chunks within same document produce same hash8
- **THEN** the system SHALL append collision counter: `{doc_id}:c{idx}#{hash8}-{n}`

### Requirement: Quality Metrics

The system SHALL compute and log chunking quality metrics for monitoring and tuning.

#### Scenario: Intra-chunk coherence

- **WHEN** chunking completes
- **THEN** the system SHALL compute mean coherence of sentences within each chunk (target ≥0.60)

#### Scenario: Boundary alignment

- **WHEN** document has section boundaries
- **THEN** the system SHALL report fraction of chunk boundaries aligned with section boundaries (target ≥70%)

#### Scenario: Size distribution

- **WHEN** chunking document
- **THEN** the system SHALL log chunk_sizes[] and verify mean ± std within target_tokens ± 100

### Requirement: Facet Generation Trigger

The system SHALL trigger facet generation for high-value chunks based on clinical intent and content.

#### Scenario: Endpoint facet trigger

- **WHEN** chunk.intent="endpoint" and contains numeric effect measure
- **THEN** the system SHALL mark chunk for facet generation (facet_types=["endpoint"])

#### Scenario: Multi-facet trigger

- **WHEN** chunk contains both PICO elements and outcomes
- **THEN** the system SHALL mark for multiple facets (facet_types=["pico", "endpoint"])

#### Scenario: Skip facet generation

- **WHEN** chunk.intent="general" and no specialized content detected
- **THEN** the system SHALL NOT generate facets (facet_types=[])

### Requirement: Write to Knowledge Graph

The system SHALL write chunks to Neo4j with edges linking to source documents and overlapping chunks.

#### Scenario: Create chunk node

- **WHEN** chunk is finalized
- **THEN** the system SHALL CREATE (:Chunk {id, text, intent, section, start, end, token_count, coherence_score})

#### Scenario: Link to document

- **WHEN** creating chunk node
- **THEN** the system SHALL CREATE (:Document)-[:HAS_CHUNK {index}]->(:Chunk)

#### Scenario: Link overlapping chunks

- **WHEN** chunk has overlap_with_prev
- **THEN** the system SHALL CREATE (:Chunk)-[:OVERLAPS {start, end}]->(:Chunk)

### Requirement: CLI and API

The system SHALL provide CLI commands and API endpoints for chunking operations.

#### Scenario: Chunk single document

- **WHEN** running `med chunk --doc-id DOC123 --profile imrad`
- **THEN** the system SHALL retrieve IR, apply profile, write chunks to KG, and return chunk_ids[]

#### Scenario: Batch chunking

- **WHEN** running `med chunk --filter source=pmc state=pdf_ir_ready --profile imrad`
- **THEN** the system SHALL process all matching documents in parallel

#### Scenario: API endpoint

- **WHEN** POST /chunk with {doc_ids[], profile?}
- **THEN** the system SHALL chunk documents and return {chunk_ids[], stats{mean_size, mean_coherence, boundary_alignment}}
