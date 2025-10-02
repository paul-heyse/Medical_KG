# Implementation Tasks

## 1. Licensing Enforcement

- [x] 1.1 Define licenses.yml schema (vocabs{SNOMED, MedDRA, LOINC, RxNorm, HPO}; each with {licensed, territory?})
- [x] 1.2 Read licenses.yml on startup; validate structure
- [x] 1.3 Disable ontology loaders if license missing (SNOMED loader checks LIC_SNOMED; MedDRA loader checks LIC_MEDDRA)
- [x] 1.4 Gate API responses (X-License-Tier header: internal/member/affiliate/public; filter SNOMED/MedDRA labels if tier insufficient)
- [x] 1.5 Log redaction events (user/service, vocab, reason, timestamp)
- [x] 1.6 Add CLI `med licensing validate` (check all required licenses present)

## 2. SHACL Validation

- [x] 2.1 Define SHACL shapes in RDF/Turtle (units_ucum.ttl, ids_codes.ttl, spans_integrity.ttl, provenance_mandatory.ttl)
- [x] 2.2 UCUM shape: dose.unit, Evidence.time_unit_ucum, Outcome.unit_ucum must exist in UCUM code list
- [x] 2.3 Code presence shape: if Evidence.outcome_loinc exists → (:Evidence)-[:MEASURES]->(:Outcome{loinc}) must exist
- [x] 2.4 Span integrity shape: spans_json non-empty; start < end; offsets within originating chunk length
- [x] 2.5 AE edge shape: (:Study)-[:HAS_AE]->(:AdverseEvent) must have count≥0, denom≥0 (if present), grade∈{1..5} (if present)
- [x] 2.6 Provenance shape: :Evidence|:EvidenceVariable|:EligibilityConstraint must have ≥1 :WAS_GENERATED_BY edge
- [x] 2.7 Implement SHACL validator (pyshacl or custom); run on batch of writes before commit
- [x] 2.8 Dead-letter queue (kg_write_deadletter) for violations with {reason, payload_hash, timestamp}

## 3. PROV Provenance

- [x] 3.1 Create :ExtractionActivity nodes (id UNIQUE, model, version, prompt_hash, schema_hash, ts ISO8601)
- [x] 3.2 Link all assertions to :ExtractionActivity via :WAS_GENERATED_BY
- [x] 3.3 Store doc content hashes (sha256 of raw bytes) in Document.meta
- [x] 3.4 Store IR hashes (sha256 of JSONL) in Document.meta
- [x] 3.5 Store MinerU provenance (run_id, version, artifacts URIs) in Document.meta for PDFs
- [x] 3.6 Store config_version and model_versions in :ExtractionActivity
- [x] 3.7 Query provenance (Cypher: match extraction → activity → model/version)

## 4. Audit Logging

- [x] 4.1 Implement audit log (write to immutable log store or WORM S3 bucket)
- [x] 4.2 Log all EL writes (mention_id, chunk_id, chosen_id, confidence, user/service, model, version, timestamp)
- [x] 4.3 Log all extraction writes (extraction_type, extraction_id, chunk_ids, user/service, model, version, timestamp)
- [x] 4.4 Log config changes (config_version old/new, changed_fields, user, timestamp)
- [x] 4.5 Log review queue actions (mention_id, action accept/correct/reject, reviewer, timestamp)
- [x] 4.6 Log licensing redaction events (vocab, caller_tier, doc_id/concept_id, timestamp)
- [x] 4.7 Structured JSON logs; index in ELK/Splunk for search

## 5. Encryption

- [x] 5.1 At rest: enable KMS encryption for S3 buckets, EBS/GCE PD volumes, Neo4j backups, OpenSearch snapshots
- [x] 5.2 In transit: enforce TLS 1.2+ for all HTTP endpoints; reject unencrypted connections
- [x] 5.3 Optional mTLS: configure service mesh (Istio/Linkerd) for service-to-service mTLS
- [x] 5.4 Secrets encryption: store API keys, DB passwords in Vault with encryption at rest

## 6. RBAC

- [x] 6.1 Define K8s ServiceAccounts per service (api, ingest, chunker, extract, kg-writer)
- [x] 6.2 Define K8s Roles + RoleBindings (least privilege; e.g., chunker can read ConfigMap, write to object store; cannot write to Neo4j)
- [x] 6.3 Define API scopes (ingest:read, ingest:write, chunk:write, embed:write, retrieve:read, map:write, extract:write, kg:write, catalog:read, admin:*)
- [x] 6.4 Enforce scopes in API middleware (reject requests with insufficient scope; return 403)
- [x] 6.5 Implement admin-only endpoints (/admin/reload, /catalog/refresh) with strict scope checks

## 7. Secrets Management

- [x] 7.1 Deploy Vault (KV secrets engine + dynamic secrets engine for DB)
- [x] 7.2 Store API keys in Vault (NCBI_EUTILS_API_KEY, OPENFDA_API_KEY, UMLS_API_KEY, etc.)
- [x] 7.3 Store DB credentials in Vault (short-lived; TTL 24h)
- [x] 7.4 Rotate secrets (quarterly for static keys; auto for dynamic DB creds)
- [x] 7.5 Inject secrets into pods via Vault agent or external-secrets operator
- [x] 7.6 Never log secrets (mask in logs and error messages)

## 8. Data Retention & Deletion

- [x] 8.1 Define retention policies (raw sources 2y, IR 2y, embeddings regenerate on-demand, KG versioned retain indefinitely with purge option)
- [x] 8.2 Implement purge pipeline (accept doc_id; delete raw → delete IR → remove chunks → remove embeddings → remove KG nodes/edges referencing doc)
- [x] 8.3 Mark deleted docs with "deleted" provenance in KG (or orphan nodes)
- [x] 8.4 S3 lifecycle policies (move to infrequent access after 90d, deep archive after 1y)
- [x] 8.5 GDPR/right-to-delete support (if EHR added: purge PHI on request)

## 9. Backups & Disaster Recovery

- [x] 9.1 OpenSearch snapshots (daily at 03:00 UTC to medkg-prod-snapshots/os/; retain 30)
- [x] 9.2 Neo4j backups (daily at 04:00 UTC to medkg-prod-snapshots/neo4j/; retain 30; PITR logs 7d)
- [x] 9.3 Object store versioning (enabled; lifecycle policies)
- [x] 9.4 Cross-region replication (optional for DR; replicate to secondary region)
- [x] 9.5 Restore runbook (document procedure; test quarterly in staging)
- [x] 9.6 RPO ≤24h (acceptable data loss); RTO ≤8h (time to restore)

## 10. Vulnerability Management

- [x] 10.1 Weekly container image scans (Trivy/Grype; fail build if high/critical CVEs)
- [x] 10.2 Base image pinning (use specific tags; update quarterly)
- [x] 10.3 Dependency lockfiles (requirements.txt with hashes; npm package-lock.json)
- [x] 10.4 SBOM generation (Syft; attach to releases)
- [x] 10.5 SAST (CodeQL/Semgrep; run in CI)

## 11. Supply Chain Security

- [x] 11.1 Sign container images (cosign; verify signatures at deployment)
- [x] 11.2 Policy enforcement (OPA/Gatekeeper; reject unsigned images)
- [x] 11.3 Verify model checksums (vLLM models, SPLADE checkpoints; SHA256 match before loading)

## 12. Network Security

- [x] 12.1 Private subnets for data stores (no public IPs)
- [x] 12.2 Security groups (restrict egress; allow only NLM, FDA, WHO, etc. endpoints)
- [x] 12.3 WAF (rate limiting, IP allowlists, SQL injection/XSS protection)
- [x] 12.4 DDoS mitigation (CloudFlare/AWS Shield)

## 13. Testing

- [x] 13.1 Unit tests for SHACL validator (valid/invalid nodes → verify pass/fail)
- [x] 13.2 Integration test licensing (query with/without entitlement → verify redaction)
- [x] 13.3 Test purge pipeline (delete doc → verify all refs removed from KG, indexes, object store)
- [x] 13.4 Test backup/restore (snapshot Neo4j → restore to new instance → verify data integrity)
- [x] 13.5 Penetration testing (hire external firm; annual or after major changes)

## 14. Documentation

- [x] 14.1 Security architecture diagram (network, encryption, RBAC)
- [x] 14.2 Licensing compliance guide (how to acquire licenses, configure licenses.yml)
- [x] 14.3 SHACL shapes reference (document each shape + common violations)
- [x] 14.4 Audit log schema and query examples
- [x] 14.5 DR runbook (restore procedure, RPO/RTO targets)
