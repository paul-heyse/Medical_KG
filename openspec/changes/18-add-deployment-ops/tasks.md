# Implementation Tasks

## 1. Operational Runbooks

- [x] 1.1 Hot config change runbook (POST /admin/reload; validate success via /version; verify config_version metric)
- [x] 1.2 Scale retrieval runbook (HPA on CPU for I/O bound; RPS autoscaler via KEDA on Kafka for request bound)
- [x] 1.3 Index rebuild runbook (create chunks_v2; dual-write; verify parity Recall@20 delta <2%; flip alias; drop old)
- [x] 1.4 Catalog refresh runbook (triggered via catalog.refresh job; ensure license gates; diff counts SNOMED/MedDRA deltas; rebuild synonyms file; rolling restart OpenSearch)
- [x] 1.5 GPU node failure runbook (cordon node; drain pods; replace/repair node; uncordon)
- [x] 1.6 vLLM down runbook (check GPU visibility, vLLM logs, restart service, verify /health endpoint)
- [x] 1.7 Neo4j failover runbook (promote read replica to core; update connection strings; verify writes)
- [x] 1.8 OpenSearch shard unassigned runbook (check disk space, cluster health, reroute shards)

## 2. E2E Verification Suite

- [x] 2.1 Ingest 10 PMC OA + 10 SPL + 10 NCT (full auto pipeline)
- [x] 2.2 Chunk, facet, embed, index (verify all steps complete)
- [x] 2.3 Run 50 gold medical queries (verify Recall@20 and nDCG@10 thresholds met)
- [x] 2.4 EL adjudication on 100 mentions (verify acceptance ≥0.70 where deterministic IDs present)
- [x] 2.5 Extraction for PICO/effects/AEs (validate against gold JSON)
- [x] 2.6 KG write (run SHACL for UCUM/codes; expect 0 violations)
- [x] 2.7 Generate sample dossier (verify all sections present + 100% citation coverage)
- [x] 2.8 E2E latency check (ingest to briefing <5 min for 10 docs)

## 3. Performance Tuning Guides

- [x] 3.1 Retrieval blend tuning (monitor component score contributions; if SPLADE down, reweight to dense=0.7, bm25=0.3)
- [x] 3.2 OpenSearch tuning (shard size 20-40 GB; refresh_interval 30s; indexing buffer 10% heap)
- [x] 3.3 Neo4j tuning (batch upserts 1000 nodes/edges/tx; dbms.memory.pagecache to dataset working set)
- [x] 3.4 GPU batch tuning (Qwen embed throughput target ≥2.5K tokens/s/GPU; adjust batch size dynamically)
- [x] 3.5 Query optimization (use EXPLAIN on slow Cypher queries; add indexes)

## 4. Cost Controls

- [x] 4.1 TTL policies for transient topics (7d)
- [x] 4.2 ILM warm/cold tiers in OpenSearch (hot 7d → warm 30d → cold 90d → delete)
- [x] 4.3 Spot GPU nodes for non-urgent backfills (use node selectors; tolerate interruptions)
- [x] 4.4 Compression (NDJSON gz; Kafka LZ4; API gzip)
- [x] 4.5 Budget alerts (AWS Cost Anomaly Detection; alert if weekly spend >$threshold)

## 5. Load Testing Suite

- [x] 5.1 Burst scenario (50 QPS for 2 min; measure P95 latency /retrieve, /extract)
- [x] 5.2 Steady scenario (10 QPS for 1 hour; verify no memory leaks, no degradation)
- [x] 5.3 Mixed intents (endpoint 40%, AE 25%, dose 15%, eligibility 10%, others 10%)
- [x] 5.4 Flamegraphs per stage (BM25, SPLADE, ANN, reranker)
- [x] 5.5 Back-pressure handling (if P95 > SLO → disable reranker, reduce topK, switch to RRF)

## 6. Chaos Testing

- [x] 6.1 Kill API pod (verify HPA scales up; requests re-route; no downtime)
- [x] 6.2 Kill vLLM pod (verify embed jobs fail gracefully; no CPU fallback; ledger remains consistent)
- [x] 6.3 Drop network to OpenSearch (verify retrieval returns 503; clients retry)
- [x] 6.4 Fill Neo4j disk (verify writes fail; alerts trigger; ops add capacity)
- [x] 6.5 GPU OOM (verify job fails with clear error; no corrupt state)

## 7. Observability Stack

- [x] 7.1 Prometheus metrics (http_requests_total, retrieve_latency_ms_bucket, fusion_component_score, el_accept_rate, extraction_span_grounding_failures, opensearch_query_latency_ms, neo4j_vector_latency_ms, config_version)
- [x] 7.2 Grafana dashboards (see Infrastructure proposal for list)
- [x] 7.3 OpenTelemetry tracing (propagate traceparent; instrument OS/Neo4j/vLLM calls; 0.1 sampling in prod)
- [x] 7.4 Structured logs (JSON; include x-request-id, trace_id, user/service, level, message, context)

## 8. Alerting Rules

- [x] 8.1 P95 /retrieve latency > 900ms for 5m → page
- [x] 8.2 EL acceptance < 0.6 hourly rolling → warn
- [x] 8.3 OpenSearch shard unassigned > 0 → page
- [x] 8.4 Neo4j core down < 3 → page
- [x] 8.5 vLLM down or GPU not visible → page
- [x] 8.6 Nightly eval regression (nDCG drop >3 points) → warn

## 9. Incident Response Playbook

- [x] 9.1 Severity definitions (P1 service down, P2 SLO breach, P3 warning thresholds, P4 maintenance)
- [x] 9.2 Escalation paths (P1 page on-call immediately; P2 page if not ack'd in 15min; P3 Slack alert)
- [x] 9.3 On-call rotation (primary + secondary; weekly rotation)
- [x] 9.4 Incident communication (status page updates; internal Slack channel)
- [x] 9.5 Post-mortem template (what happened, timeline, root cause, action items, prevention)

## 10. Release Checklist

- [x] 10.1 All metrics meet thresholds (Chunking boundary alignment ≥65%, Retrieval nDCG@10 ≥baseline+5, Recall@20 per family ≥targets, EL ID accuracy ≥0.90, EL concepts ≥0.85, Extraction effects F1 ≥0.80, AE mapping ≥0.80, Faithfulness 100%, SHACL 0 violations, Latency P95 within SLOs)
- [x] 10.2 No CPU fallback events detected (query logs for GPU enforcement failures; expect 0)
- [x] 10.3 Licenses validated (SNOMED/UMLS/MedDRA per policy.yaml)
- [x] 10.4 Provenance coverage = 100% (all :Evidence/:EvidenceVariable/:EligibilityConstraint have :WAS_GENERATED_BY)
- [x] 10.5 SHACL pass-rate ≥ 0.98 (units, IDs, code presence, ranges)
- [x] 10.6 Backups verified (Neo4j, OpenSearch, object store; restore tested)
- [x] 10.7 Rollback plan tested on staging
- [x] 10.8 Sign-off from domain lead, engineering lead, ops lead

## 11. Operational Metrics Dashboards

- [x] 11.1 Pipeline throughput (docs ingested/hour, chunks created/hour, embeddings computed/hour)
- [x] 11.2 Indexing lag (<10 min for non-PDF auto path; PDF lag depends on manual MinerU trigger)
- [x] 11.3 GPU utilization (vLLM, SPLADE, MinerU; aim 80-90% under load)
- [x] 11.4 Error rates (ingest failures, chunk failures, embed failures, extract failures per type)
- [x] 11.5 User-facing latency (P50/P95/P99 for /retrieve, /extract, /briefing)

## 12. Continuous Improvement

- [x] 12.1 Weekly metrics review (ops + eng; identify trends, regressions, optimization opportunities)
- [x] 12.2 Monthly quality review (domain lead + eng; review extraction samples, update gold sets)
- [x] 12.3 Quarterly DR drill (restore from backups; verify RTO/RPO targets)
- [x] 12.4 Quarterly security review (vulnerability scans, penetration test, audit logs review)

## 13. Testing

- [x] 13.1 E2E test in dev (full pipeline; verify all steps pass)
- [x] 13.2 Load test in staging (burst + steady; measure P95)
- [x] 13.3 Chaos test in staging (kill pods; verify resilience)
- [x] 13.4 Release dry-run in staging (deploy, run E2E, rollback)

## 14. Documentation

- [x] 14.1 Deployment guide (prerequisites, Terraform apply, Helm install, post-deploy verification)
- [x] 14.2 Operations manual (runbooks, incident response, on-call guide)
- [x] 14.3 Performance tuning guide (retrieval weights, GPU batching, index optimization)
- [x] 14.4 Cost optimization guide (TTL policies, ILM, spot instances)
- [x] 14.5 DR procedure (restore from backups, failover regions, RPO/RTO targets)
