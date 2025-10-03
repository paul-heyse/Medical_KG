# Core APIs Capability

## ADDED Requirements

### Requirement: OpenAPI 3.1 Specification

The system SHALL provide REST APIs defined by OpenAPI 3.1 specification with complete schema definitions.

#### Scenario: OpenAPI document

- **WHEN** accessing /openapi.json
- **THEN** the system SHALL return valid OpenAPI 3.1 document with all endpoints, schemas, security definitions

#### Scenario: API documentation

- **WHEN** accessing /docs
- **THEN** the system SHALL serve Swagger UI or ReDoc with interactive API documentation

#### Scenario: Schema validation

- **WHEN** request is received
- **THEN** the system SHALL validate request body against OpenAPI schema and return 400 with field-level errors if invalid

### Requirement: Authentication and Authorization

The system SHALL enforce OAuth2 client credentials flow with scope-based authorization.

#### Scenario: OAuth2 token acquisition

- **WHEN** POST /oauth/token with {client_id, client_secret, grant_type: "client_credentials"}
- **THEN** the system SHALL return {access_token, token_type: "Bearer", expires_in, scope}

#### Scenario: API key fallback

- **WHEN** request includes X-API-Key header
- **THEN** the system SHALL validate API key and allow access for internal jobs

#### Scenario: Scope enforcement

- **WHEN** endpoint requires scope "extract:write" and token lacks scope
- **THEN** the system SHALL return 403 Forbidden with error "Insufficient scope"

### Requirement: Idempotency Support

The system SHALL support idempotency for write operations using Idempotency-Key header.

#### Scenario: Idempotent request

- **WHEN** POST /ingest with Idempotency-Key=UUID and same request body
- **THEN** the system SHALL return cached result from first request (within 24h TTL)

#### Scenario: Key collision with different body

- **WHEN** POST request uses same Idempotency-Key with different body
- **THEN** the system SHALL return 409 Conflict with error "Idempotency key already used with different request"

#### Scenario: Key expiration

- **WHEN** Idempotency-Key is older than 24h
- **THEN** the system SHALL process as new request and generate new idempotency entry

### Requirement: Rate Limiting

The system SHALL enforce rate limits per API key or client_id with X-RateLimit headers.

#### Scenario: Rate limit headers

- **WHEN** responding to any request
- **THEN** the system SHALL include X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset headers

#### Scenario: Rate limit exceeded

- **WHEN** client exceeds rate limit
- **THEN** the system SHALL return 429 Too Many Requests with Retry-After header

#### Scenario: Configurable limits

- **WHEN** rate limit configuration changes
- **THEN** the system SHALL apply new limits from config.yaml without restart (hot-reload)

### Requirement: Licensing Enforcement in APIs

The system SHALL filter API responses based on X-License-Tier header per vocabulary licensing.

#### Scenario: Public tier filtering

- **WHEN** request includes X-License-Tier=public
- **THEN** the system SHALL redact SNOMED/MedDRA/UMLS labels (return concept IRIs and open codes only)

#### Scenario: Member tier access

- **WHEN** request includes X-License-Tier=member
- **THEN** the system SHALL return LOINC and RxNorm data but redact SNOMED/MedDRA/UMLS

#### Scenario: Affiliate tier access

- **WHEN** request includes X-License-Tier=affiliate
- **THEN** the system SHALL return all licensed vocabulary data

### Requirement: Ingest Endpoints

The system SHALL provide POST /ingest/{source} endpoints for triggering document ingestion.

#### Scenario: Ingest ClinicalTrials

- **WHEN** POST /ingest/clinicaltrials with {nct_ids[], auto: true}
- **THEN** the system SHALL fetch studies, parse, validate, write IR, and return {status: "success", doc_ids[], errors[]}

#### Scenario: Ingest PDF

- **WHEN** POST /ingest/pdf with {uri, doc_key}
- **THEN** the system SHALL download PDF, persist to object store, set ledger state=pdf_downloaded, and return {status: "success", ledger_state: "pdf_downloaded"}

#### Scenario: Batch ingestion

- **WHEN** POST /ingest/pmc with {pmcids[], auto: true}
- **THEN** the system SHALL process each PMCID and return {status: "success", doc_ids[], errors[]}

### Requirement: Processing Endpoints

The system SHALL provide endpoints for chunking, embedding, and indexing operations.

#### Scenario: Chunk documents

- **WHEN** POST /chunk with {doc_ids[], profile: "imrad"}
- **THEN** the system SHALL chunk documents and return {chunk_ids[], stats{mean_size, mean_coherence, boundary_alignment}}

#### Scenario: Embed objects

- **WHEN** POST /embed with {object_ids[], object_type: "chunk"|"facet"|"concept", modality: "dense"|"splade"|"both"}
- **THEN** the system SHALL compute embeddings and return {embedded_count, failed[]}

#### Scenario: Index chunks

- **WHEN** POST /index/chunks with {chunk_ids[]}
- **THEN** the system SHALL index to OpenSearch and return {indexed_count, failed[]}

### Requirement: Retrieval Endpoint

The system SHALL provide POST /retrieve for multi-retriever fusion search.

#### Scenario: Basic retrieval

- **WHEN** POST /retrieve with {query, topK: 20}
- **THEN** the system SHALL execute fusion retrieval and return {results[{chunk_id, text, scores{bm25, splade, dense, final}}], query_meta{timing, component_scores}}

#### Scenario: Intent-aware retrieval

- **WHEN** POST /retrieve with {query, intent: "endpoint"}
- **THEN** the system SHALL boost endpoint facets and return relevant results

#### Scenario: Filtered retrieval

- **WHEN** POST /retrieve with {query, filters: {source: ["pmc"], date_range: {gte: "2020-01-01"}}}
- **THEN** the system SHALL apply filters and return matching results

### Requirement: Extraction Endpoints

The system SHALL provide POST /extract/{type} endpoints for clinical extraction.

#### Scenario: Extract PICO

- **WHEN** POST /extract/pico with {chunk_ids[]}
- **THEN** the system SHALL extract PICO and return {extractions[{chunk_id, pico{population, interventions, outcomes, evidence_spans}}]}

#### Scenario: Extract effects

- **WHEN** POST /extract/effects with {chunk_ids[]}
- **THEN** the system SHALL extract effect measures and return {extractions[]}

#### Scenario: Extract adverse events

- **WHEN** POST /extract/ae with {chunk_ids[]}
- **THEN** the system SHALL extract AEs and return {extractions[]}

### Requirement: Entity Linking Endpoints

The system SHALL provide endpoints for candidate generation and adjudication.

#### Scenario: Generate candidates

- **WHEN** POST /map/candidates with {doc_id, chunk_id, mentions[{text, start, end}]}
- **THEN** the system SHALL return {candidates[{mention_id, candidates[{iri, label, score, ontology}]}]}

#### Scenario: Adjudicate entity linking

- **WHEN** POST /map/el with {mention, candidates[], context}
- **THEN** the system SHALL return {chosen_id, ontology, score, evidence_span, alternates[]}

### Requirement: Knowledge Graph Endpoints

The system SHALL provide POST /kg/write for upserting nodes and edges.

#### Scenario: Write nodes and edges

- **WHEN** POST /kg/write with {nodes[], edges[], provenance{model, version, ts}}
- **THEN** the system SHALL upsert to Neo4j and return {written_count, failed[]}

#### Scenario: SHACL validation

- **WHEN** writing to KG
- **THEN** the system SHALL validate via SHACL shapes and reject invalid data to dead-letter queue

### Requirement: Briefing Endpoints

The system SHALL provide endpoints for generating topic dossiers and evidence maps.

#### Scenario: Generate dossier

- **WHEN** POST /briefing/dossier with {topic{condition, intervention, outcome}, format: "md"|"html"|"json"}
- **THEN** the system SHALL query KG, synthesize evidence, and return {dossier, citations[]}

#### Scenario: Generate evidence map

- **WHEN** POST /briefing/evidence-map with {topic}
- **THEN** the system SHALL return {map[], conflicts[], gaps[]}

#### Scenario: Real-time Q&A

- **WHEN** POST /briefing/qa with {query}
- **THEN** the system SHALL retrieve, extract, synthesize and return {answer, evidence[], confidence}

### Requirement: Health and Version Endpoints

The system SHALL provide GET /health and GET /version for monitoring.

#### Scenario: Health check

- **WHEN** GET /health
- **THEN** the system SHALL return {status: "ok"|"degraded"|"down", services{opensearch, neo4j, vllm}, timestamp}

#### Scenario: Version info

- **WHEN** GET /version
- **THEN** the system SHALL return {api_version, component_versions{}, model_versions{qwen, splade}}

### Requirement: Error Handling

The system SHALL return structured error responses with retriable flag and support references.

#### Scenario: Validation error

- **WHEN** request fails validation
- **THEN** the system SHALL return 400 with {code: "VALIDATION_ERROR", message, details[{field, error}], retriable: false}

#### Scenario: Upstream timeout

- **WHEN** OpenSearch query times out
- **THEN** the system SHALL return 504 with {code: "UPSTREAM_TIMEOUT", message, retriable: true, reference: "<https://docs.../runbooks/timeout"}>

#### Scenario: License denied

- **WHEN** unlicensed vocabulary requested
- **THEN** the system SHALL return 403 with {code: "LICENSE_DENIED", message: "SNOMED requires affiliate license", retriable: false}

### Requirement: Tracing and Request IDs

The system SHALL propagate W3C traceparent and x-request-id for observability.

#### Scenario: Generate request ID

- **WHEN** request lacks x-request-id
- **THEN** the system SHALL generate UUIDv4 and include in response header and all logs

#### Scenario: Trace context propagation

- **WHEN** request includes traceparent header
- **THEN** the system SHALL propagate to all downstream services (OpenSearch, Neo4j, vLLM)

### Requirement: Monitoring Metrics

The system SHALL emit comprehensive API metrics.

#### Scenario: Request metrics

- **WHEN** handling requests
- **THEN** the system SHALL emit http_requests_total{route, method, status}, http_request_duration_seconds_bucket{route}

#### Scenario: Business metrics

- **WHEN** operations complete
- **THEN** the system SHALL emit ingest_docs_total{source}, retrieve_queries_total{intent}, extract_success_rate{type}
