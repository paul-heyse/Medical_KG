# Concept Catalog Capability

## ADDED Requirements

### Requirement: Ontology Loaders

The system SHALL provide loaders for 10+ medical ontologies with incremental updates and version tracking.

#### Scenario: SNOMED CT loader

- **WHEN** loading SNOMED CT RF2 distribution
- **THEN** the system SHALL parse Concept, Description, and Relationship files and create (:Concept) nodes with SNOMED codes, FSN, synonyms, and IS_A hierarchy

#### Scenario: ICD-11 loader

- **WHEN** fetching from WHO ICD API
- **THEN** the system SHALL authenticate with OAuth2, download MMS linearization, and extract codes, titles, definitions, parents, inclusions/exclusions

#### Scenario: LOINC loader

- **WHEN** loading LOINC distribution
- **THEN** the system SHALL parse LOINC codes with component, property, time, system, scale, method attributes and create concept nodes

### Requirement: Concept Normalization

The system SHALL normalize concepts to consistent schema with IRIs, codes, labels, definitions, and hierarchies.

#### Scenario: IRI assignment

- **WHEN** loading concept from any ontology
- **THEN** the system SHALL assign canonical IRI (e.g., "<http://snomed.info/id/73211009>" for diabetes mellitus)

#### Scenario: Label normalization

- **WHEN** concept has multiple names (FSN, preferred term, synonyms)
- **THEN** the system SHALL set label=preferred_term and store all synonyms in synonyms[] array

#### Scenario: Definition extraction

- **WHEN** available in source ontology
- **THEN** the system SHALL extract definition and store in Concept.definition field

### Requirement: Hierarchy Management

The system SHALL build and query ontology hierarchies for subsumption reasoning.

#### Scenario: IS_A relationships

- **WHEN** loading hierarchical ontology (SNOMED, ICD, HPO)
- **THEN** the system SHALL create (:Concept)-[:IS_A]->(:Concept) edges for parent-child relationships

#### Scenario: Transitive closure

- **WHEN** hierarchy is loaded
- **THEN** the system SHALL compute transitive closure and store ancestor/descendant counts

#### Scenario: Subsumption query

- **WHEN** querying for concepts subsumed by "Diabetes Mellitus"
- **THEN** the system SHALL return all descendant concepts via IS_A* path traversal

### Requirement: Cross-Vocabulary Mappings

The system SHALL load and maintain mappings between ontologies (e.g., SNOMED ↔ ICD-10, LOINC ↔ SNOMED).

#### Scenario: SNOMED to ICD-10 mapping

- **WHEN** loading SNOMED CT ICD-10 map
- **THEN** the system SHALL create (:Concept)-[:MAPS_TO {source, confidence}]->(:Concept) edges

#### Scenario: UMLS CUI crosswalk

- **WHEN** integrating UMLS
- **THEN** the system SHALL group concepts by CUI and create :SAME_AS edges for equivalent concepts across vocabularies

#### Scenario: RxNorm to SNOMED mapping

- **WHEN** querying drug concept in RxNorm
- **THEN** the system SHALL return SNOMED CT equivalents via MAPS_TO edges

### Requirement: Synonym and Label Search

The system SHALL enable fuzzy search over concept labels and synonyms with ranking.

#### Scenario: Exact label match

- **WHEN** searching for "Diabetes Mellitus"
- **THEN** the system SHALL return concepts with exact label match ranked first

#### Scenario: Synonym match

- **WHEN** searching for "Sugar Diabetes"
- **THEN** the system SHALL return SNOMED concept for Diabetes Mellitus via synonym match

#### Scenario: Fuzzy search

- **WHEN** searching for "diabetis" (typo)
- **THEN** the system SHALL use Levenshtein distance ≤2 and return "Diabetes" concepts with lower score

### Requirement: Concept Embeddings

The system SHALL compute and store embeddings for all concepts enabling dense semantic search.

#### Scenario: Embedding generation

- **WHEN** catalog refresh completes
- **THEN** the system SHALL compute Qwen embeddings for concatenated label + definition + synonyms (first 3)

#### Scenario: Embedding storage

- **WHEN** embeddings are computed
- **THEN** the system SHALL store in Neo4j as Concept.embedding_qwen and create vector index

#### Scenario: Dense search

- **WHEN** querying by embedding
- **THEN** the system SHALL use cosine similarity via Neo4j vector index and return top-K concepts

### Requirement: SPLADE Expansion

The system SHALL compute SPLADE term expansions for concepts enabling sparse retrieval.

#### Scenario: SPLADE doc-side expansion

- **WHEN** processing concept
- **THEN** the system SHALL compute SPLADE vector and extract top-50 terms with weights >0.5

#### Scenario: Expansion storage

- **WHEN** SPLADE expansion completes
- **THEN** the system SHALL store as Concept.splade_terms[] and index in OpenSearch

#### Scenario: Sparse search

- **WHEN** querying concepts via SPLADE
- **THEN** the system SHALL match expanded terms and score using BM25F

### Requirement: License Enforcement

The system SHALL gate access to licensed vocabularies (SNOMED, UMLS, MedDRA) based on policy configuration.

#### Scenario: Licensed vocabulary check

- **WHEN** loading SNOMED CT and LIC_SNOMED is not set in policy.yaml
- **THEN** the system SHALL refuse to load and exit with error "SNOMED requires affiliate license"

#### Scenario: Runtime filtering

- **WHEN** API request includes X-License-Tier=public
- **THEN** the system SHALL filter out SNOMED/MedDRA/UMLS concepts or redact labels (return IDs only)

#### Scenario: License metadata

- **WHEN** storing concept
- **THEN** the system SHALL set Concept.license_bucket=open|member|affiliate and filter queries accordingly

### Requirement: Catalog Refresh

The system SHALL support incremental and full catalog refreshes with minimal downtime.

#### Scenario: Full refresh

- **WHEN** running `med catalog refresh --full`
- **THEN** the system SHALL download all ontologies, rebuild concept nodes/edges, compute embeddings, and flip alias to new version

#### Scenario: Incremental update

- **WHEN** running `med catalog refresh --ontology loinc --incremental`
- **THEN** the system SHALL download delta since last version, apply changes (new, updated, retired concepts), and recompute affected embeddings

#### Scenario: Version tracking

- **WHEN** refresh completes
- **THEN** the system SHALL record catalog_version with {ontology: version_date} mapping and emit as metric

### Requirement: Three Retrieval Modalities

The system SHALL support dictionary (exact/fuzzy), SPLADE (sparse), and dense (Qwen) retrieval for concept candidates.

#### Scenario: Dictionary retrieval

- **WHEN** mention="enalapril maleate"
- **THEN** the system SHALL search OpenSearch concepts_v1 index with multi_match on label^2 and synonyms and return top-20 with BM25 scores

#### Scenario: SPLADE retrieval

- **WHEN** mention="chest pain"
- **THEN** the system SHALL expand via SPLADE model, search splade_terms field, and return top-20 with BM25F scores

#### Scenario: Dense retrieval

- **WHEN** mention="elevated blood sugar"
- **THEN** the system SHALL embed via Qwen, search Neo4j vector index concept_qwen_idx, and return top-20 with cosine similarity scores

### Requirement: Concept Metadata

The system SHALL store rich metadata for each concept to support filtering and provenance.

#### Scenario: Ontology source

- **WHEN** concept is loaded
- **THEN** the system SHALL set Concept.ontology=SNOMED|ICD11|LOINC|RxNorm|MeSH|HPO|MONDO|MedDRA|CTCAE|GUDID

#### Scenario: Semantic type

- **WHEN** available (e.g., UMLS semantic types)
- **THEN** the system SHALL set Concept.semantic_types[] (e.g., ["Disease or Syndrome", "Clinical Finding"])

#### Scenario: Status and retirement

- **WHEN** concept is retired or deprecated
- **THEN** the system SHALL set Concept.status=retired and Concept.retired_date and exclude from active searches

### Requirement: API Endpoints

The system SHALL provide API endpoints for concept search and retrieval.

#### Scenario: Search endpoint

- **WHEN** POST /catalog/search with {query, modality: dict|splade|dense, topK}
- **THEN** the system SHALL return concepts[] with {iri, codes, label, score, ontology}

#### Scenario: Lookup by code

- **WHEN** GET /catalog/concept/{ontology}/{code}
- **THEN** the system SHALL return concept details with {iri, codes, label, definition, synonyms, parents, children, mappings}

#### Scenario: Hierarchy query

- **WHEN** GET /catalog/concept/{iri}/descendants
- **THEN** the system SHALL return all descendant concepts via IS_A* traversal
