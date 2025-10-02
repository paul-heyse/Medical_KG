# Add Core APIs (REST with OpenAPI 3.1)

## Why

Production-ready REST APIs enable integration with external systems, orchestration tools, and user interfaces. OpenAPI 3.1 specification ensures discoverability, client code generation, and API contract validation. Comprehensive API surface covers ingestion, processing, retrieval, extraction, and KG operations.

## What Changes

- Define OpenAPI 3.1 specification (base: `https://api.<org>.medkg/v1`)
- Implement REST endpoints:
  - `/ingest/{source}` (POST: trigger ingestion for clinicaltrials, dailymed, pmc, pdf, etc.)
  - `/chunk` (POST: run semantic chunker on IR documents)
  - `/embed` (POST: compute SPLADE + Qwen embeddings for chunks/facets/concepts)
  - `/retrieve` (POST: multi-retriever fusion with intent routing)
  - `/map/candidates` (POST: generate EL candidates for mentions)
  - `/map/el` (POST: LLM adjudication for entity linking)
  - `/extract/{type}` (POST: run PICO/effects/ae/dose/eligibility extractors)
  - `/kg/write` (POST: upsert nodes/edges with span-grounded properties)
  - `/catalog/refresh` (POST: trigger ontology catalog rebuild)
  - `/health` (GET: liveness/readiness probe)
  - `/version` (GET: component and model versions)
- Add authentication (OAuth2 client credentials + API key fallback)
- Implement idempotency (Idempotency-Key header; 24h dedup)
- Add unified error envelope (code, message, details[], retriable, reference)
- Implement rate limiting (X-RateLimit-* headers)
- Add licensing enforcement (X-License-Tier header; filter SNOMED/MedDRA/UMLS per caller tier)
- Implement tracing (W3C traceparent, x-request-id propagation)

## Impact

- **Affected specs**: NEW `core-apis` capability
- **Affected code**: NEW `/api/handlers/`, `/api/middleware/`, `/api/openapi.yaml`
- **Dependencies**: All backend services (ingest, chunk, embed, retrieve, extract, kg); Auth service; rate limiter
- **Downstream**: Frontend/dashboards consume APIs; orchestration tools call APIs; external integrations
- **SLOs**: P95 latency varies by endpoint (ingest ≤2s, retrieve ≤700ms, extract ≤3s)
