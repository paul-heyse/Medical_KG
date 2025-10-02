# Implementation Tasks

## 1. OpenAPI 3.1 Specification

- [ ] 1.1 Define openapi.yaml (info, servers, security, paths, components/schemas, components/responses)
- [ ] 1.2 Define request/response schemas for each endpoint
- [ ] 1.3 Define error schema (code enum, message, details[], retriable, reference)
- [ ] 1.4 Add security schemes (OAuth2, ApiKeyAuth)
- [ ] 1.5 Generate API documentation (Swagger UI / ReDoc)

## 2. Authentication & Authorization

- [ ] 2.1 Implement OAuth2 client credentials flow (token endpoint, JWT validation)
- [ ] 2.2 Implement API key fallback (for internal jobs; key in header or query param)
- [ ] 2.3 Define scopes (ingest:read, ingest:write, chunk:write, embed:write, retrieve:read, map:write, extract:write, kg:write, catalog:read, admin:*)
- [ ] 2.4 Add middleware to enforce scopes per endpoint
- [ ] 2.5 Return 401 Unauthorized or 403 Forbidden with clear error messages

## 3. Idempotency

- [ ] 3.1 Accept Idempotency-Key header (UUIDv4)
- [ ] 3.2 Store hash(body + key) in cache (Redis/DB; TTL 24h)
- [ ] 3.3 Return cached result if key+body match within 24h
- [ ] 3.4 Return 409 Conflict if key exists with different body

## 4. Rate Limiting

- [ ] 4.1 Implement rate limiter (per API key or client_id; configurable limits per scope)
- [ ] 4.2 Return X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset headers
- [ ] 4.3 Return 429 Too Many Requests with Retry-After header

## 5. Tracing & Request ID

- [ ] 5.1 Accept traceparent header (W3C Trace Context)
- [ ] 5.2 Generate x-request-id (UUIDv4) if not provided
- [ ] 5.3 Propagate both to all downstream services
- [ ] 5.4 Log correlation IDs in all log entries

## 6. Licensing Enforcement

- [ ] 6.1 Accept X-License-Tier header (internal, member, affiliate, public)
- [ ] 6.2 Filter SNOMED/MedDRA/UMLS labels/definitions per tier (return IDs always; redact text if unlicensed)
- [ ] 6.3 Log redaction events with caller info
- [ ] 6.4 Return partial results with warning if some data redacted

## 7. Unified Error Handling

- [ ] 7.1 Define error envelope schema
- [ ] 7.2 Map exceptions to error codes (VALIDATION_ERROR, LICENSE_DENIED, NOT_FOUND, RETRYABLE, UPSTREAM_TIMEOUT, INTERNAL)
- [ ] 7.3 Include field-level validation errors in details[]
- [ ] 7.4 Return retriable flag (true for 429, 502, 503, 504; false for 400, 401, 403, 404)
- [ ] 7.5 Include reference to support doc or runbook URL

## 8. Endpoint Implementations

- [ ] 8.1 POST /ingest/clinicaltrials (body: {nct_ids[], auto?}; return: {status, doc_ids[], errors[]})
- [ ] 8.2 POST /ingest/dailymed (body: {setids[], auto?})
- [ ] 8.3 POST /ingest/pmc (body: {pmcids[], auto?})
- [ ] 8.4 POST /ingest/pdf (body: {uri, doc_key}; return: {status, ledger_state})
- [ ] 8.5 POST /chunk (body: {doc_ids[], profile?}; return: {chunk_ids[], stats})
- [ ] 8.6 POST /embed (body: {object_ids[], object_type: chunk|facet|concept}; return: {embedded_count, failed[]})
- [ ] 8.7 POST /retrieve (body: {query, intent?, filters?, topK?, rerank_enabled?}; return: {results[], query_meta})
- [ ] 8.8 POST /map/candidates (body: {doc_id, chunk_id, mentions[]}; return: {candidates[]})
- [ ] 8.9 POST /map/el (body: {mention, candidates[], context}; return: {chosen_id, ontology, score, evidence_span, alternates[]})
- [ ] 8.10 POST /extract/pico (body: {chunk_ids[]}; return: {extractions[]})
- [ ] 8.11 POST /extract/effects, /extract/ae, /extract/dose, /extract/eligibility (similar structure)
- [ ] 8.12 POST /kg/write (body: {nodes[], edges[], provenance}; return: {written_count, failed[]})
- [ ] 8.13 POST /catalog/refresh (body: {sources[]?}; return: {status, refresh_id})
- [ ] 8.14 GET /health (return: {status: ok|degraded|down, services{}, timestamp})
- [ ] 8.15 GET /version (return: {api_version, component_versions{}, model_versions{}})

## 9. Middleware Stack

- [ ] 9.1 Request logging (method, path, status, duration, x-request-id)
- [ ] 9.2 CORS (configurable allowed origins)
- [ ] 9.3 Request size limits (10MB default; configurable per endpoint)
- [ ] 9.4 Content-Type validation (accept application/json; optionally text/event-stream for streaming, application/x-ndjson for bulk)
- [ ] 9.5 Response compression (gzip if Accept-Encoding: gzip)

## 10. Streaming & Bulk APIs (Optional)

- [ ] 10.1 POST /ingest/batch (accept application/x-ndjson; stream ingestion results)
- [ ] 10.2 GET /retrieve/stream (Server-Sent Events for progressive results)
- [ ] 10.3 POST /extract/batch (NDJSON input/output for bulk extraction)

## 11. Observability

- [ ] 11.1 Emit metrics (http_requests_total{route, method, code}, http_request_duration_seconds_bucket{route})
- [ ] 11.2 Emit business metrics (ingest_docs_total{source}, retrieve_queries_total{intent}, extract_success_rate{type})
- [ ] 11.3 Add /metrics endpoint (Prometheus format)

## 12. Testing

- [ ] 12.1 Unit tests for each handler (mock services; verify request/response shapes)
- [ ] 12.2 Integration tests (hit real endpoints; verify E2E flows)
- [ ] 12.3 Test auth (valid/invalid tokens, missing scopes)
- [ ] 12.4 Test idempotency (same key+body → same result; different body → 409)
- [ ] 12.5 Test rate limiting (exceed limit → 429)
- [ ] 12.6 Test error handling (malformed JSON, validation errors, upstream timeouts)
- [ ] 12.7 Load test (100 QPS; measure P95 latency per endpoint)

## 13. Documentation

- [ ] 13.1 Generate API docs from OpenAPI spec (host on /docs)
- [ ] 13.2 Create getting-started guide (auth, first request, common patterns)
- [ ] 13.3 Document error codes and troubleshooting
- [ ] 13.4 Provide example requests/responses (curl, Python, TypeScript)
