# Add Security & Compliance (Licensing, SHACL, Provenance, Audit)

## Why

Medical KG handles licensed vocabularies (SNOMED, UMLS, MedDRA), requires audit trails for regulatory compliance, and must ensure data integrity via validation (SHACL). Comprehensive security controls (encryption, RBAC, secrets management) and provenance (PROV) enable trustworthy, production-grade operations.

## What Changes

- Implement licensing enforcement: read licenses.yml on startup; gate loaders (SNOMED/UMLS/MedDRA); filter query results per X-License-Tier; log redaction events
- Add SHACL validation: define shapes (UCUM units, code presence, span integrity, AE edge properties, provenance mandatory); run pre-KG write; dead-letter violations
- Implement PROV provenance: every assertion links to :ExtractionActivity (model, version, prompt_hash, schema_hash, ts); store doc/IR content hashes; track MinerU run IDs
- Add audit logging: immutable logs (WORM or log store immutability); log all EL/extraction writes, config changes, review queue actions
- Implement encryption: at rest (KMS for object store, DB volumes); in transit (TLS everywhere; optional mTLS for service-to-service)
- Add RBAC: K8s namespaced roles; API scopes (ingest:write, kg:write, admin:*); least privilege
- Implement secrets management: Vault/KMS; short-lived DB credentials (dynamic secrets); 30-day rotation
- Add data retention & deletion: retention policies (raw sources 2y, IR 2y, embeddings on-demand, KG versioned); purge pipeline (delete doc → remove chunks → remove embeddings → remove KG nodes/edges)
- Implement backups & DR: daily snapshots (Neo4j, OpenSearch, object store); cross-region replication (optional); restore runbook; RPO ≤24h, RTO ≤8h

## Impact

- **Affected specs**: NEW `security-compliance` capability
- **Affected code**: NEW `/kg/shacl/`, `/security/licensing/`, `/security/audit/`, `/security/vault/`, updates to all writers
- **Dependencies**: Vault/KMS, audit log store, SHACL validator, licenses.yml
- **Downstream**: All writes validated; all queries filtered by license tier; all changes audited
- **Compliance**: Licensing terms respected; audit trail for investigations; data purge on request
