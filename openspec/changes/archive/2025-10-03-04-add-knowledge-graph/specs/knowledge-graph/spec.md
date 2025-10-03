# Knowledge Graph Capability

## ADDED Requirements

### Requirement: Neo4j CDKO-Med Schema

The system SHALL implement CDKO-Med schema in Neo4j with comprehensive node types and relationships for medical knowledge representation.

#### Scenario: Document nodes

- **WHEN** ingesting documents
- **THEN** the system SHALL CREATE (:Document {id, source, uri, title, language, publication_date, meta}) with UNIQUE constraint on id

#### Scenario: Chunk nodes

- **WHEN** creating chunks
- **THEN** the system SHALL CREATE (:Chunk {id, text, intent, section, start, end, token_count, coherence_score}) with UNIQUE constraint on id

#### Scenario: Concept nodes

- **WHEN** loading ontologies
- **THEN** the system SHALL CREATE (:Concept {iri, codes, label, definition, synonyms, ontology, semantic_types, license_bucket}) with UNIQUE constraint on iri

### Requirement: Clinical Evidence Nodes

The system SHALL create specialized nodes for clinical evidence including Evidence, EvidenceVariable, AdverseEvent, and Intervention.

#### Scenario: Evidence nodes

- **WHEN** extracting effect measures
- **THEN** the system SHALL CREATE (:Evidence {id, type, value, ci_low, ci_high, p_value, n_total, model, time_unit_ucum, certainty, spans_json})

#### Scenario: EvidenceVariable nodes

- **WHEN** extracting PICO
- **THEN** the system SHALL CREATE (:EvidenceVariable {id, population_json, interventions_json, comparators_json, outcomes_json, timeframe, spans_json})

#### Scenario: AdverseEvent nodes

- **WHEN** extracting AEs
- **THEN** the system SHALL CREATE (:AdverseEvent {id, term, meddra_pt, grade, count, denom, arm, serious, onset_days, spans_json})

### Requirement: Study and Trial Nodes

The system SHALL represent clinical trials and studies with structured metadata.

#### Scenario: Study nodes

- **WHEN** ingesting ClinicalTrials.gov entries
- **THEN** the system SHALL CREATE (:Study {nct_id, title, phase, status, conditions, interventions_json, arms_json, eligibility_json})

#### Scenario: StudyArm nodes

- **WHEN** trial has multiple arms
- **THEN** the system SHALL CREATE (:StudyArm {id, label, type, n_enrolled, intervention_summary})

#### Scenario: Eligibility constraints

- **WHEN** extracting eligibility
- **THEN** the system SHALL CREATE (:EligibilityConstraint {id, type, logic_json, human_text, spans_json})

### Requirement: Relationship Types

The system SHALL define comprehensive relationship types for connecting nodes with typed edges.

#### Scenario: Document-Chunk relationships

- **WHEN** chunks are created
- **THEN** the system SHALL CREATE (:Document)-[:HAS_CHUNK {index}]->(:Chunk)

#### Scenario: Chunk-Concept relationships

- **WHEN** entity linking completes
- **THEN** the system SHALL CREATE (:Chunk)-[:MENTIONS {confidence, start, end, quote, negated?, hypothetical?}]->(:Concept)

#### Scenario: Evidence relationships

- **WHEN** writing evidence
- **THEN** the system SHALL CREATE (:Study)-[:REPORTS]->(:Evidence), (:Evidence)-[:MEASURES]->(:Outcome:Concept)

#### Scenario: Provenance relationships

- **WHEN** writing extractions
- **THEN** the system SHALL CREATE (:Evidence|:EvidenceVariable)-[:WAS_GENERATED_BY]->(:ExtractionActivity)

### Requirement: Constraints and Indexes

The system SHALL create constraints and indexes for data integrity and query performance.

#### Scenario: Unique constraints

- **WHEN** initializing schema
- **THEN** the system SHALL CREATE CONSTRAINT FOR (d:Document) REQUIRE d.id IS UNIQUE, similar for Chunk.id, Concept.iri, Study.nct_id

#### Scenario: Property indexes

- **WHEN** optimizing queries
- **THEN** the system SHALL CREATE INDEX FOR (c:Chunk) ON (c.intent), (c.section), (c.doc_id)

#### Scenario: Composite indexes

- **WHEN** filtering by source and date
- **THEN** the system SHALL CREATE INDEX FOR (d:Document) ON (d.source, d.publication_date)

### Requirement: Vector Indexes

The system SHALL create vector indexes for dense retrieval over chunks and concepts.

#### Scenario: Chunk vector index

- **WHEN** chunk embeddings computed
- **THEN** the system SHALL CREATE VECTOR INDEX chunk_qwen_idx FOR (c:Chunk) ON c.embedding_qwen WITH {indexProvider: "lucene", dimensions: 4096, similarityFunction: "cosine"}

#### Scenario: Concept vector index

- **WHEN** concept embeddings computed
- **THEN** the system SHALL CREATE VECTOR INDEX concept_qwen_idx FOR (c:Concept) ON c.embedding_qwen WITH {dimensions: 4096, similarityFunction: "cosine"}

#### Scenario: Vector search query

- **WHEN** dense retrieval executes
- **THEN** the system SHALL use db.index.vector.queryNodes(index, topK, queryVector) to find nearest neighbors

### Requirement: SHACL Validation

The system SHALL validate KG writes against SHACL shapes for data integrity.

#### Scenario: UCUM shape

- **WHEN** writing Evidence or Dose nodes
- **THEN** the system SHALL validate unit fields against UCUM code list via SHACL

#### Scenario: Code presence shape

- **WHEN** writing Evidence with outcome_loinc
- **THEN** the system SHALL validate (:Evidence)-[:MEASURES]->(:Outcome{loinc}) edge exists

#### Scenario: Span integrity shape

- **WHEN** writing nodes with spans_json
- **THEN** the system SHALL validate spans_json non-empty, start < end, offsets within source text

#### Scenario: Provenance mandatory shape

- **WHEN** writing Evidence/EvidenceVariable/EligibilityConstraint
- **THEN** the system SHALL validate ≥1 :WAS_GENERATED_BY edge exists

### Requirement: Batch Write Operations

The system SHALL support batch writes for performance with transaction consistency.

#### Scenario: Batch MERGE

- **WHEN** writing 1000 concepts
- **THEN** the system SHALL use APOC batch operations CALL apoc.periodic.iterate() with batchSize=1000

#### Scenario: Transaction atomicity

- **WHEN** batch write fails mid-transaction
- **THEN** the system SHALL rollback all changes in transaction and log failure

#### Scenario: Write throughput

- **WHEN** ingesting large documents
- **THEN** the system SHALL achieve ≥500 nodes/edges per second write throughput

### Requirement: FHIR Export

The system SHALL export KG data to FHIR R4/R5 resources for interoperability.

#### Scenario: Evidence resource export

- **WHEN** exporting Evidence nodes
- **THEN** the system SHALL generate FHIR Evidence resources with statistic, certainty, and variableDefinition

#### Scenario: ResearchStudy export

- **WHEN** exporting Study nodes
- **THEN** the system SHALL generate FHIR ResearchStudy resources with identifier, condition, arm, and outcome

#### Scenario: AdverseEvent resource export

- **WHEN** exporting AdverseEvent nodes
- **THEN** the system SHALL generate FHIR AdverseEvent resources with event, seriousness, and outcome

### Requirement: Query API

The system SHALL provide Cypher query API for complex graph traversals.

#### Scenario: Find related evidence

- **WHEN** querying "Find all evidence for drug X in condition Y"
- **THEN** the system SHALL execute Cypher MATCH (:Concept{label:"X"})<-[:MENTIONS]-(:Chunk)<-[:HAS_CHUNK]-(:Document)-[:REPORTS]->(:Evidence)-[:MEASURES]->(:Outcome)<-[:MENTIONS]-(:Chunk)<-[:HAS_CHUNK]-(:Document{condition:"Y"})

#### Scenario: Subsumption reasoning

- **WHEN** querying "Find evidence for diabetes and subtypes"
- **THEN** the system SHALL traverse IS_A* hierarchy and return evidence for all descendant conditions

#### Scenario: Provenance tracing

- **WHEN** querying extraction provenance
- **THEN** the system SHALL follow :WAS_GENERATED_BY edges to :ExtractionActivity nodes with model versions

### Requirement: Monitoring and Metrics

The system SHALL emit KG metrics for health monitoring.

#### Scenario: Node/edge counts

- **WHEN** monitoring KG health
- **THEN** the system SHALL emit kg_nodes_total{label}, kg_edges_total{type}

#### Scenario: Write throughput

- **WHEN** writing to KG
- **THEN** the system SHALL emit kg_write_duration_seconds, kg_write_throughput_per_second

#### Scenario: SHACL violations

- **WHEN** validation executes
- **THEN** the system SHALL emit kg_shacl_violations_total{shape}

### Requirement: Backup and Versioning

The system SHALL support backups and version tracking for KG data.

#### Scenario: Daily backups

- **WHEN** backup schedule triggers
- **THEN** the system SHALL execute neo4j-admin dump to backup location with timestamp

#### Scenario: Version metadata

- **WHEN** major KG changes occur
- **THEN** the system SHALL track kg_version in metadata node with {version, timestamp, change_summary}

#### Scenario: Point-in-time recovery

- **WHEN** restoring from backup
- **THEN** the system SHALL support PITR logs for 7 days of transaction replay
