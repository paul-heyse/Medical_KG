# Security and Compliance Capability

## ADDED Requirements

### Requirement: Licensing Enforcement

The system SHALL enforce vocabulary licensing per policy.yaml and filter query results by X-License-Tier.

#### Scenario: Load licenses.yml

- **WHEN** service initializes
- **THEN** the system SHALL read licenses.yml with vocabs{SNOMED{licensed, territory}, MedDRA{licensed}, UMLS{licensed}} and validate structure

#### Scenario: Gate loaders

- **WHEN** SNOMED loader invoked and LIC_SNOMED=false
- **THEN** the system SHALL refuse to load and exit with error "SNOMED requires affiliate license"

#### Scenario: Filter by license tier

- **WHEN** API request includes X-License-Tier=public
- **THEN** the system SHALL redact SNOMED/MedDRA/UMLS labels (return IRIs only)

#### Scenario: Log redaction events

- **WHEN** filtering licensed data
- **THEN** the system SHALL log {user/service, vocab, reason, timestamp} to audit log

### Requirement: SHACL Validation

The system SHALL validate KG writes against SHACL shapes for data integrity.

#### Scenario: UCUM shape

- **WHEN** writing Evidence or Dose nodes
- **THEN** the system SHALL validate dose.unit, Evidence.time_unit_ucum against UCUM code list

#### Scenario: Code presence shape

- **WHEN** Evidence has outcome_loinc
- **THEN** the system SHALL validate (:Evidence)-[:MEASURES]->(:Outcome{loinc}) edge exists

#### Scenario: Span integrity shape

- **WHEN** writing nodes with spans_json
- **THEN** the system SHALL validate spans_json non-empty, start < end, offsets within source text length

#### Scenario: Provenance mandatory shape

- **WHEN** writing Evidence/EvidenceVariable/EligibilityConstraint
- **THEN** the system SHALL validate ≥1 :WAS_GENERATED_BY edge exists or reject

#### Scenario: Dead-letter on violation

- **WHEN** SHACL validation fails
- **THEN** the system SHALL write to kg_write_deadletter with {reason, payload_hash, timestamp}

### Requirement: PROV Provenance

The system SHALL store comprehensive provenance linking assertions to extraction activities.

#### Scenario: Create ExtractionActivity nodes

- **WHEN** extraction runs
- **THEN** the system SHALL CREATE (:ExtractionActivity {id, model, version, prompt_hash, schema_hash, ts})

#### Scenario: Link assertions to activity

- **WHEN** writing Evidence/EvidenceVariable/AdverseEvent
- **THEN** the system SHALL CREATE (:Assertion)-[:WAS_GENERATED_BY]->(:ExtractionActivity)

#### Scenario: Store content hashes

- **WHEN** ingesting documents
- **THEN** the system SHALL compute SHA256 of raw bytes and store in Document.meta.content_hash

#### Scenario: Track model versions

- **WHEN** storing provenance
- **THEN** ExtractionActivity SHALL include config_version, model_versions{}

### Requirement: Audit Logging

The system SHALL log all EL/extraction writes, config changes, and review queue actions to immutable log store.

#### Scenario: Log EL writes

- **WHEN** entity linking creates MENTIONS edge
- **THEN** the system SHALL log {mention_id, chunk_id, chosen_id, confidence, user/service, model, version, timestamp} to audit log

#### Scenario: Log extraction writes

- **WHEN** clinical extraction writes nodes
- **THEN** the system SHALL log {extraction_type, extraction_id, chunk_ids, user/service, model, version, timestamp}

#### Scenario: Log config changes

- **WHEN** config hot-reload executes
- **THEN** the system SHALL log {config_version_old, config_version_new, changed_fields[], user, timestamp}

#### Scenario: Log review queue actions

- **WHEN** reviewer accepts/corrects/rejects mention
- **THEN** the system SHALL log {mention_id, action, reviewer, timestamp}

#### Scenario: Immutable storage

- **WHEN** writing audit logs
- **THEN** logs SHALL be written to WORM S3 bucket or log store with immutability guarantees

### Requirement: Encryption

The system SHALL enforce encryption at rest (KMS) and in transit (TLS 1.2+).

#### Scenario: Encryption at rest

- **WHEN** storing data
- **THEN** S3 buckets, EBS/GCE PD volumes, Neo4j backups, OpenSearch snapshots SHALL use KMS encryption

#### Scenario: Encryption in transit

- **WHEN** serving APIs
- **THEN** all HTTP endpoints SHALL enforce TLS 1.2+ and reject unencrypted connections

#### Scenario: Optional mTLS

- **WHEN** service mesh enabled
- **THEN** service-to-service communication SHALL use mTLS

#### Scenario: Secrets encryption

- **WHEN** storing secrets in Vault
- **THEN** Vault SHALL use encryption at rest for all secret data

### Requirement: RBAC

The system SHALL enforce role-based access control with least privilege per service and API scope.

#### Scenario: K8s ServiceAccounts

- **WHEN** deploying services
- **THEN** each service SHALL have dedicated ServiceAccount with minimal RBAC permissions

#### Scenario: API scopes

- **WHEN** API request requires scope "kg:write"
- **THEN** middleware SHALL verify token includes scope or return 403

#### Scenario: Admin-only endpoints

- **WHEN** accessing /admin/reload or /catalog/refresh
- **THEN** the system SHALL require admin scope and reject without it

### Requirement: Secrets Management

The system SHALL store secrets in Vault with short-lived credentials and 30-day rotation.

#### Scenario: Store API keys in Vault

- **WHEN** managing secrets
- **THEN** NCBI_EUTILS_API_KEY, UMLS_API_KEY, etc. SHALL be stored in Vault KV engine

#### Scenario: Dynamic DB credentials

- **WHEN** services connect to Neo4j/OpenSearch
- **THEN** Vault SHALL provide short-lived credentials (TTL 24h) via dynamic secrets engine

#### Scenario: Rotate secrets

- **WHEN** rotation schedule triggers
- **THEN** static API keys SHALL rotate quarterly; dynamic DB creds auto-rotate

#### Scenario: Inject secrets into pods

- **WHEN** deploying to K8s
- **THEN** Vault agent or external-secrets operator SHALL inject secrets as env vars or mounted files

#### Scenario: Never log secrets

- **WHEN** logging
- **THEN** the system SHALL mask all fields matching *_KEY,*_SECRET, *_TOKEN patterns

### Requirement: Data Retention and Deletion

The system SHALL enforce retention policies and support data purge on request.

#### Scenario: Retention policies

- **WHEN** defining retention
- **THEN** raw sources 2y, IR 2y, embeddings regenerate on-demand, KG versioned retain indefinitely with purge option

#### Scenario: Purge pipeline

- **WHEN** doc_id purge requested
- **THEN** the system SHALL delete raw → IR → chunks → embeddings → KG nodes/edges referencing doc

#### Scenario: S3 lifecycle

- **WHEN** storing objects
- **THEN** S3 lifecycle policies SHALL move to infrequent access after 90d, deep archive after 1y

#### Scenario: GDPR support

- **WHEN** EHR added in future
- **THEN** the system SHALL support right-to-delete for PHI on request

### Requirement: Backups and Disaster Recovery

The system SHALL implement daily backups with RPO ≤24h, RTO ≤8h.

#### Scenario: OpenSearch snapshots

- **WHEN** backup schedule triggers (03:00 UTC daily)
- **THEN** the system SHALL create snapshot to medkg-prod-snapshots/os/, retain 30 days

#### Scenario: Neo4j backups

- **WHEN** backup schedule triggers (04:00 UTC daily)
- **THEN** the system SHALL execute neo4j-admin dump to medkg-prod-snapshots/neo4j/, retain 30 days, PITR logs 7d

#### Scenario: Cross-region replication

- **WHEN** DR enabled
- **THEN** the system SHALL replicate backups to secondary region for disaster recovery

#### Scenario: Test restore quarterly

- **WHEN** DR drill executes
- **THEN** the system SHALL restore from backups to test environment and verify data integrity

### Requirement: Vulnerability Management

The system SHALL scan containers weekly and fail builds on high/critical CVEs.

#### Scenario: Container scanning

- **WHEN** building images
- **THEN** CI SHALL run Trivy/Grype and fail if high/critical CVEs detected

#### Scenario: Base image pinning

- **WHEN** defining Dockerfiles
- **THEN** images SHALL use specific tags (not :latest) and update quarterly

#### Scenario: Dependency lockfiles

- **WHEN** managing dependencies
- **THEN** Python SHALL use requirements.txt with hashes; npm SHALL use package-lock.json

#### Scenario: SBOM generation

- **WHEN** releasing
- **THEN** CI SHALL generate SBOM via Syft and attach to release

### Requirement: Supply Chain Security

The system SHALL sign container images and verify checksums for models.

#### Scenario: Sign images

- **WHEN** pushing images
- **THEN** CI SHALL sign with cosign and store signatures

#### Scenario: Verify signatures

- **WHEN** deploying to K8s
- **THEN** OPA/Gatekeeper policy SHALL reject unsigned images

#### Scenario: Verify model checksums

- **WHEN** loading vLLM models or SPLADE checkpoints
- **THEN** the system SHALL verify SHA256 matches expected checksum before loading

### Requirement: Network Security

The system SHALL enforce private subnets, WAF, and egress allowlists.

#### Scenario: Private subnets

- **WHEN** deploying data stores
- **THEN** OpenSearch, Neo4j, Kafka, Redis SHALL be in private subnets with no public IPs

#### Scenario: WAF for API

- **WHEN** exposing API
- **THEN** ALB/NLB SHALL have WAF with rate limiting, IP allowlists, SQL injection/XSS protection

#### Scenario: Egress allowlist

- **WHEN** configuring network
- **THEN** security groups SHALL allow egress only to NLM, FDA, WHO, etc. endpoints (no unrestricted internet)
